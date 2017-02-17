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
            for event in payload:
                # Find a push event and find the last commit made
                if event['type'] == 'PushEvent':
                    sha = event['payload']['head']
                    job_queue.append(sha)
                    break
                elif event['type'] == 'CreateEvent':
                    if event['payload']['ref_type'] == 'branch':
                        branch = event['payload']['ref']
                        sha = self._get_last_commit_on_branch(branch)
                        job_queue.append(sha)
                    break
            else:
                print('No new commits')

    def _request_events(self):
        r = requests.get('https://api.github.com/repos/ScreamingUdder/mantid/events',
                         headers={'If-None-Match': self.e_tag},
                         auth=('matthew-d-jones', self.github_token))
        if r.status_code == 200:
            self.e_tag = r.headers['ETag']
        return r

    def _request_branch_info(self, branch):
        r = requests.get('https://api.github.com/repos/ScreamingUdder/mantid/branches/' + branch,
                         auth=('matthew-d-jones', self.github_token))
        return r

    def _get_last_commit_on_branch(self, branch):
        r = self._request_branch_info(branch)
        payload = r.json()
        return payload['commit']['sha']
