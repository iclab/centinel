from base64 import urlsafe_b64encode
import glob
import hashlib
import os.path

# Use this list to randomly choose a User-Agent string
user_agent_pool = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0",
    # Microsoft Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36 Edge/16.16299",
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36 OPR/43.0.2442.991",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/601.7.7 (KHTML, like Gecko) Version/9.1.2 Safari/601.7.7"
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
