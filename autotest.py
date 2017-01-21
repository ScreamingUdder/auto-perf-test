from git import Repo, Git
import time
import requests
import sys
from slackclient import SlackClient
from kafka_test_utils import KafkaSubprocess

#TODO send data to broker once and set topic to clear data on size NOT on age!
# Then don't need to run the producer every time the performance test is run

repo_path = '../mantid.git'
build_path = 'mantid-build'
slack_token = sys.argv[0]
github_token = sys.argv[1]
sc = SlackClient(slack_token)


def checkout(sha):
    g = Git(repo_path)
    repo = Repo(repo_path)
    assert not repo.bare
    repo.remotes.origin.fetch()
    g.checkout(sha)
    repo.remotes.origin.pull()


def report_to_slack(sha):
    sc.api_call(
        "chat.postMessage",
        channel="#test_slackclient",
        text="Built new commit: https://github.com/ScreamingUdder/mantid/commit/"+sha
    )


def build_new_commit(sha):
    checkout(sha)
    # Build Mantid
    buildProcess = KafkaSubprocess('cmake -B'+build_path+' -H'+repo_path)
    build_output = buildProcess.wait()
    print build_output
    #TODO Run the performance test script
    #TODO Put results on webpage
    report_to_slack(sha)



def poll_github():
    """Poll github for new commits, build Mantid and run perf test for latest commit"""
    r = requests.get('https://api.github.com/repos/ScreamingUdder/mantid/events',
                     auth=('matthew-d-jones', github_token))
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
    pass


def main():
    # Poll slack once every 2 seconds and github once every 30 seconds
    while True:
        for _ in range(15):
            time.sleep(2)
            poll_slack()
        poll_github()


if __name__ == "__main__":
    main()
