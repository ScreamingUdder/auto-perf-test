from git import Repo, Git
import time
import requests
import sys
from slackclient import SlackClient
import subprocess

REPO_PATH = '../mantid'
BUILD_PATH = '../mantid-build'
SLACK_TOKEN = sys.argv[1]
BOT_ID = sys.argv[2]
GITHUB_TOKEN = sys.argv[3]
sc = SlackClient(SLACK_TOKEN)
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


def start_build_commit(job_queue):
    """Returns handle to process doing build and logfile of stdout"""
    # Get first job in the queue
    sha = job_queue.pop(0)
    checkout(sha)
    status = 'building'
    # Build Mantid
    logfile = open('build_log', 'w+')
    return subprocess.Popen(
        'cmake3 -DENABLE_MANTIDPLOT=OFF -DENABLE_OPENCASCADE=OFF -B' + BUILD_PATH + ' -H' + REPO_PATH + '; make -j8 -C ' + BUILD_PATH + ' Framework',
        stdout=logfile, shell=True), logfile, status


def poll_for_process_end(process, logfile, status):
    """Returns True if process ended"""
    if status != 'idle':
        if process.poll() is not None:
            logfile.close()
            if status == 'building':
                process, logfile, status = start_perf_test()
            else:
                status = 'idle'
    return process, logfile, status


def start_perf_test():
    """Returns handle to process doing test and logfile of stdout"""
    status = 'testing'
    logfile = open('test_log', 'w+')
    return subprocess.Popen([BUILD_PATH + '/bin/mantidpython', 'test.py'], stdout=logfile), logfile, status


def commit_exists(sha):
    """Check if a commit exists, return True if it does, otherwise False"""
    r = requests.get('https://api.github.com/repos/ScreamingUdder/mantid/commits/' + sha,
                     auth=('matthew-d-jones', GITHUB_TOKEN))
    return r.status_code == 200


def poll_github(job_queue):
    """Poll github for new commits, build Mantid and run perf test for latest commit"""
    r = requests.get('https://api.github.com/repos/ScreamingUdder/mantid/events',
                     auth=('matthew-d-jones', GITHUB_TOKEN))
    if r.status_code == 200:
        payload = r.json()
        for something in payload:
            # Find a push event and find the last commit made
            if something['type'] == 'PushEvent':
                sha = something['payload']['commits'][-1]['sha']
                job_queue.append(sha)
                break
        else:
            print('No new commits')


def poll_slack(job_queue):
    """Poll slack for new messages to the bot"""
    command, channel = parse_slack_output(sc.rtm_read())
    if command and channel:
        handle_command(command, channel, job_queue)


def handle_command(command, channel, job_queue):
    """If command is valid then act on it, otherwise inform user"""
    response = "Not a recognised command"
    split_command = command.strip().split()
    if command.startswith('test'):
        sha = split_command[1]
        if commit_exists(sha):
            if len(job_queue) > 0:
                response = "Added job to queue"
            else:
                response = "Executing build and test at commit " + sha
            job_queue.append(sha)
        else:
            response = "I couldn't find that commit"
    elif command.startswith('clear queue'):
        del job_queue[:]
        response = "Queue is cleared"
    elif command.startswith('show queue'):
        response = "Queue: " + ", ".join(job_queue)
    elif command.startswith('help'):
        response = "Commands: \"show queue\",\"clear queue\",\"test <COMMIT>\""
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
        status = 'idle'
        job_queue = []
        process = None
        logfile = None
        # Poll slack once every 2 seconds and github once every 30 seconds
        while True:
            if status == 'idle' and len(job_queue) > 0:
                process, logfile, status = start_build_commit(job_queue)
            else:
                process, logfile, status = poll_for_process_end(process, logfile, status)
            for _ in range(15):
                time.sleep(2)
                poll_slack(job_queue)
            poll_github(job_queue)
    else:
        print('Failed to connect to Slack bot, check token and bot ID')


if __name__ == "__main__":
    main()
