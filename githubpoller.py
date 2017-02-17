import requests


class GithubPoller:
    def __init__(self, github_token):
        self.github_token = github_token
        # Use etag to avoid getting unchanged data back from github each poll
        self.e_tag = ''
        self._request_events()

    def poll(self, job_queue):
        """Poll github for new commits, if there are new ones add a build job for latest commit"""
        r = self._request_events()
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

    def _request_events(self):
        r = requests.get('https://api.github.com/repos/ScreamingUdder/mantid/events',
                         headers={'If-None-Match': self.e_tag},
                         auth=('matthew-d-jones', self.github_token))
        self.e_tag = r.headers['ETag']
        return r
