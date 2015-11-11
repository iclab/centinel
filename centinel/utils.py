from base64 import urlsafe_b64encode
import glob
import hashlib
import os.path

# Use this list to randomly choose a User-Agent string
user_agent_pool = [
    # Chrome
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.80 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1",
    # Internet Explorer
    "Mozilla/5.0 (compatible, MSIE 11, Windows NT 6.3; Trident/7.0; rv:11.0) like Gecko",
    # Maxthon
    "Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/533.1 "
    "(KHTML, like Gecko) Maxthon/3.0.8.2 Safari/533.1",
    # Opera
    "Opera/9.80 (X11; Linux i686; Ubuntu/14.10) Presto/2.12.388 Version/12.16",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.75.14 "
    "(KHTML, like Gecko) Version/7.0.3 Safari/7046A194A",
    # MyIE2
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; MyIE2; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0)"
]


def hash_folder(folder, regex='[!_]*'):
    """
    Get the md5 sum of each file in the folder and return to the user

    :param folder: the folder to compute the sums over
    :param regex: an expression to limit the files we match
    :return:

    Note: by default we will hash every file in the folder

    Note: we will not match anything that starts with an underscore

    """
    file_hashes = {}
    for path in glob.glob(os.path.join(folder, regex)):
        # exclude folders
        if not os.path.isfile(path):
            continue

        with open(path, 'r') as fileP:
            md5_hash = hashlib.md5(fileP.read()).digest()

        file_name = os.path.basename(path)
        file_hashes[file_name] = urlsafe_b64encode(md5_hash)
    return file_hashes


def compute_files_to_download(client_hashes, server_hashes):
    """
    Given a dictionary of file hashes from the client and the
    server, specify which files should be downloaded from the server

    :param client_hashes: a dictionary where the filenames are keys and the
                          values are md5 hashes as strings
    :param server_hashes: a dictionary where the filenames are keys and the
                          values are md5 hashes as strings
    :return: a list of 2 lists -> [to_dload, to_delete]
             to_dload- a list of filenames to get from the server
             to_delete- a list of filenames to delete from the folder

    Note: we will get a file from the server if a) it is not on the
    client or b) the md5 differs between the client and server

    Note: we will mark a file for deletion if it is not available on
    the server

    """
    to_dload, to_delete = [], []
    for filename in server_hashes:
        if filename not in client_hashes:
            to_dload.append(filename)
            continue
        if client_hashes[filename] != server_hashes[filename]:
            to_dload.append(filename)

    for filename in client_hashes:
        if filename not in server_hashes:
            to_delete.append(filename)

    return [to_dload, to_delete]
