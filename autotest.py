from git import Repo, Git
import time
import requests

#TODO send data to broker once and set topic to clear data on size NOT on age!
# Then don't need to run the producer every time the performance test is run

#TODO accept path to mantid repo as input arg

# report to slack? (create a new channel on mantidslack for it and invite Lamar)

repo_path = '../mantid.git'


def checkout(sha):
    g = Git(repo_path)
    repo = Repo(repo_path)
    assert not repo.bare
    repo.remotes.origin.fetch()
    g.checkout(sha)
    repo.remotes.origin.pull()


def build_new_commit(sha):
    checkout(sha)
    #TODO now build Mantid
    #TODO Run the performance test script
    #TODO Put results on webpage
    #TODO Report to Slack


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
        time.sleep(10)
        print('loop end')


if __name__ == "__main__":
    main()
