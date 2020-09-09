from datacroaker import SingleVersionRemoteDataSource
from datacroaker import DataSourceVersion
from datacroaker.helper import downloader
from datacroaker.helper.filehandler import unzip


class Hmdb(SingleVersionRemoteDataSource):

    def __init__(self, root_dir):
        """
        initialize datasource with a root directory
        :param root_dir: root directory path
        :type root_dir: str
        """
        super(Hmdb, self).__init__(root_dir)

    def latest_remote_version(self):
        """
        Only the latest version is accessible.
        """
        return DataSourceVersion('4.0')

    def download_function(self, instance, version):

        files = [
            'https://hmdb.ca/system/downloads/current/structures.zip',
            'https://hmdb.ca/system/downloads/current/hmdb_metabolites.zip',
            'https://hmdb.ca/system/downloads/current/hmdb_proteins.zip'
        ]

        for file in files:
            downloaded_zip = downloader.download_file_to_dir(file, instance.process_instance_dir)
            unzip(downloaded_zip)
