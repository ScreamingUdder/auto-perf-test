from git import Repo, Git
import time
import requests
import sys
from slackclient import SlackClient
from kafka-test-utils/kafka_test_utils import KafkaSubprocess

# TODO send data to broker once and set topic to clear data on size NOT on age!
# Then don't need to run the producer every time the performance test is run

REPO_PATH = '../mantid.git'
BUILD_PATH = 'mantid-build'
SLACK_TOKEN = sys.argv[0]
GITHUB_TOKEN = sys.argv[2]
sc = SlackClient(SLACK_TOKEN)
BOT_ID = sys.argv[1]
AT_BOT = "<@" + BOT_ID + ">"


def checkout(sha):
    g = Git(REPO_PATH)
    repo = Repo(REPO_PATH)
    assert not repo.bare
    repo.remotes.origin.fetch()
    g.checkout(sha)
    repo.remotes.origin.pull()


def report_to_slack(sha):
    sc.api_call(
        "chat.postMessage",
        channel="#test_slackclient",
        text="Built new commit: https://github.com/ScreamingUdder/mantid/commit/" + sha
    )


def build_new_commit(sha):
    checkout(sha)
    # Build Mantid
    buildProcess = KafkaSubprocess('cmake -B' + BUILD_PATH + ' -H' + REPO_PATH)
    build_output = buildProcess.wait()
    print build_output
    # TODO Run the performance test script
    # TODO Put results on webpage
    report_to_slack(sha)


def poll_github():
    """Poll github for new commits, build Mantid and run perf test for latest commit"""
    r = requests.get('https://api.github.com/repos/ScreamingUdder/mantid/events',
                     auth=('matthew-d-jones', GITHUB_TOKEN))
    if r.status_code == 200:
        payload = r.json()
        for something in payload:
            # Find a push event and find the last commit made
            if something['type'] == 'PushEvent':
                sha = something['payload']['commits'][-1]['sha']
                build_new_commit(sha)
                break
        else:
            print('No new commits')


def poll_slack():
    """Poll slack for new messages to the bot"""
    command, channel = parse_slack_output(sc.rtm_read())
    if command and channel:
        handle_command(command, channel)


def handle_command(command, channel):
    """If command is valid then act on it, otherwise inform user"""
    response = "Not a recognised command"
    if command.startswith('build'):
        response = "Not yet implemented"
    sc.api_call("chat.postMessage", channel=channel,
                text=response, as_user=True)


def parse_slack_output(slack_rtm_output):
    """Return any commands directed at the bot"""
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # return text after the @ mention, whitespace removed
                return output['text'].split(AT_BOT)[1].strip().lower(), \
                       output['channel']
    return None, None


def main():
    if sc.rtm_connect():
        # Poll slack once every 2 seconds and github once every 30 seconds
        while True:
            for _ in range(15):
                time.sleep(2)
                poll_slack()
            poll_github()
    else:
        print('Failed to connect to Slack bot, check token and bot ID')


if __name__ == "__main__":
    main()
