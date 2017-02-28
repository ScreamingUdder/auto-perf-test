from git import Repo, Git
import time
import datetime
import requests
import sys
import os
from slackclient import SlackClient
import subprocess
from transferdata import TransferData
import shutil
import websocket
from githubpoller import GithubPoller

REPO_PATH = os.environ['MANTID_SRC_PATH']
BUILD_PATH = os.environ['MANTID_BUILD_PATH']
SLACK_TOKEN = os.environ['SLACK_TOKEN']
BOT_ID = os.environ['BOT_ID']
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
DROPBOX_TOKEN = os.environ['DROPBOX_TOKEN']
sc = SlackClient(SLACK_TOKEN)
transfer_data = TransferData(DROPBOX_TOKEN)
AT_BOT = "<@" + BOT_ID + ">"


class CurrentJob:
    def __init__(self, sha):
        self.sha = sha
        self.output_directory = '/' + datetime.datetime.utcnow().isoformat() + '_' + sha[:7]


def checkout(sha):
    g = Git(REPO_PATH)
    repo = Repo(REPO_PATH)
    assert not repo.bare
    repo.remotes.origin.fetch()
    g.checkout(sha)


def report_to_slack(message):
    sc.api_call(
        "chat.postMessage",
        channel="#test_slackclient",
        text=message, as_user=True
    )


def start_build_commit(job_queue):
    """Returns handle to process doing build and logfile of stdout"""
    # Get first job in the queue
    sha = job_queue.pop(0)
    checkout(sha)
    status = 'building'
    report_to_slack('Starting build at commit ' + sha)
    # Build Mantid
    logfile = open('build_log.txt', 'w+')
    return subprocess.Popen(
        'cmake3 -DENABLE_MANTIDPLOT=OFF -DENABLE_OPENCASCADE=OFF -B' + BUILD_PATH + ' -H' + REPO_PATH + '; make -j8 -C ' + BUILD_PATH + ' Framework',
        stdout=logfile, stderr=subprocess.STDOUT, shell=True), logfile, status, CurrentJob(sha)


def clear_build_directory():
    """Remove all contents of the build directory (to do clean build)"""
    for the_file in os.listdir(BUILD_PATH):
        file_path = os.path.join(BUILD_PATH, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(e)


def record_live_data_duration(sha):
    """Record MonitorLiveData duration in a log file and update it on dropbox"""
    # Get MonitorLiveData duration line from mantid.log
    log_line = subprocess.check_output(['tail', '-1', '/root/.mantid/mantid.log']).split()
    timestamp_iso8601 = log_line[0] + 'T' + log_line[1].split(',')[0]
    duration_seconds = log_line[-2]
    # Append it to our duration log
    duration_filename = 'duration_log.txt'
    with open(duration_filename, 'a') as duration_log:
        duration_log.write(','.join([timestamp_iso8601, duration_seconds, sha]) + '\n')
    if os.path.isfile(duration_filename):
        transfer_data.overwrite_file(duration_filename, '/' + duration_filename)


def poll_for_process_end(process, logfile, status, current_job):
    """Returns True if process ended"""
    if status != 'idle':
        if process.poll() is not None:
            logfile.close()
            if status == 'building':
                upload('build_log.txt', current_job.output_directory)
                process, logfile, status = start_perf_test()
            else:
                upload('test_log.txt', current_job.output_directory)
                upload_all_svg(current_job.output_directory)
                status = 'idle'
                report_to_slack(
                    'Completed build and test for https://api.github.com/repos/ScreamingUdder/mantid/commits/' +
                    current_job.sha + '\nOutput files are available here: ' + transfer_data.get_link(
                        current_job.output_directory))
                record_live_data_duration(current_job.sha)
    return process, logfile, status


def upload_all_svg(output_dir):
    """Upload all files with svg extension from current directory"""
    files = [f for f in os.listdir('.') if os.path.isfile(f) and f.endswith('.svg')]
    for f in files:
        upload(f, output_dir)


def upload(filename, output_dir):
    """If file exists then try to upload it to Dropbox then delete it"""
    if os.path.isfile(filename):
        transfer_data.upload_file(filename,
                                  output_dir + '/' + filename)
        os.remove(filename)


def start_perf_test():
    """Returns handle to process doing test and logfile of stdout and stderr"""
    status = 'testing'
    logfile = open('test_log.txt', 'w+')
    # Use Agg backend to avoid problems with no display on server
    my_env = os.environ.copy()
    my_env["MPLBACKEND"] = "Agg"
    return subprocess.Popen([BUILD_PATH + '/bin/mantidpython', '--classic', 'mantidperftest.py'],
                            stdout=logfile, stderr=subprocess.STDOUT, env=my_env), logfile, status


def commit_exists(sha):
    """Check if a commit exists, return True if it does, otherwise False"""
    r = requests.get('https://api.github.com/repos/ScreamingUdder/mantid/commits/' + sha,
                     auth=('matthew-d-jones', GITHUB_TOKEN))
    return r.status_code == 200


def poll_slack(job_queue, enable_build_on_push, status):
    """Poll slack for new messages to the bot"""
    try:
        message = sc.rtm_read()
        command, channel = parse_slack_output(message)
        if command and channel:
            handle_command(command, channel, job_queue, enable_build_on_push, status)
    except websocket._exceptions.WebSocketConnectionClosedException:
        sc.rtm_connect()
    return enable_build_on_push


def handle_command(command, channel, job_queue, enable_build_on_push, status):
    """If command is valid then act on it, otherwise inform user"""
    response = "Not a recognised command"
    split_command = command.strip().split()
    if command.startswith('test'):
        sha = split_command[1]
        if commit_exists(sha):
            if len(job_queue) > 0:
                response = "Added job to queue"
            else:
                response = "Queued build and test at commit https://github.com/ScreamingUdder/mantid/commit/" + sha
            job_queue.append(sha)
        else:
            response = "I couldn't find that commit"
    elif command.startswith('clear queue'):
        del job_queue[:]
        response = "Queue is cleared"
    elif command.startswith('show queue'):
        response = "Queue: " + ", ".join(job_queue)
    elif command.startswith('enable build on git push'):
        enable_build_on_push = True
        response = "The last commit in each push to github will be built and tested"
    elif command.startswith('disable build on git push'):
        enable_build_on_push = False
        response = "Disabled building on push to github"
    elif command.startswith('clear build directory'):
        clear_build_directory()
        response = "The build directory has been cleared, ready for a clean build"
    elif command.startswith('show status'):
        response = 'Status: ' + status
    elif command.startswith('help'):
        response = 'Commands:\n\"' + '\"\n\"'.join(['show queue',
                                                    'clear queue',
                                                    'test <COMMIT>',
                                                    'enable build on git push',
                                                    'disable build on git push',
                                                    'clear build directory',
                                                    'show status',
                                                    'help']) + '\"'
    sc.api_call("chat.postMessage", channel=channel,
                text=response, as_user=True)
    return enable_build_on_push


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
        # Start up the flask app
        my_env = os.environ.copy()
        my_env["MPLBACKEND"] = "Agg"
        subprocess.Popen(['python', 'flaskapp/app.py'], env=my_env)

        gp = GithubPoller(GITHUB_TOKEN)
        status = 'idle'
        job_queue = []
        process = None
        logfile = None
        enable_build_on_push = True
        current_job = CurrentJob('')
        # Poll slack once every 2 seconds and github once every 30 seconds
        while True:
            if status == 'idle' and len(job_queue) > 0:
                process, logfile, status, current_job = start_build_commit(job_queue)
            else:
                process, logfile, status = poll_for_process_end(process, logfile, status, current_job)
            for _ in range(15):
                time.sleep(2)
                enable_build_on_push = poll_slack(job_queue, enable_build_on_push, status)
            if enable_build_on_push:
                gp.poll(job_queue)
    else:
        print('Failed to connect to Slack bot, check token and bot ID')


if __name__ == "__main__":
    main()
