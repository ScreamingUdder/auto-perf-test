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
        text="Built new commit: "+sha
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


def main():
    while True:
        # Poll github API for new events
        r = requests.get('https://api.github.com/repos/ScreamingUdder/mantid/events',
                         auth=('matthew-d-jones', 'd48ee8fe2e649d81c5839a64640eede7f15bef01'))
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
        print('sleeping')
        time.sleep(30)
        print('loop end')


if __name__ == "__main__":
    main()
