import dropbox


class TransferData:
    def __init__(self, access_token):
        self.access_token = access_token
        self.dbx = dropbox.Dropbox(self.access_token)

    def upload_file(self, file_from, file_to):
        """Upload a file to Dropbox"""

        with open(file_from, 'rb') as f:
            self.dbx.files_upload(f.read(), file_to)

    def overwrite_file(self, file_from, file_to):
        """Overwrite a file on Dropbox"""

        with open(file_from, 'rb') as f:
            self.dbx.files_upload(f.read(), file_to, mode=dropbox.files.WriteMode.overwrite)

    def get_link(self, location):
        link = self.dbx.sharing_create_shared_link_with_settings(location)
        return link.url
