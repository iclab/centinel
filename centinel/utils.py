from base64 import urlsafe_b64encode
import glob
import hashlib
import os.path

# Use this list to randomly choose a User-Agent string , updated Dec 4 2018
user_agent_pool = [
    # Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36",
    # Chrome2
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36",
    # Chrome3
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36",
    # Chrome4
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:63.0) Gecko/20100101 Firefox/63.0",
    # Firerox2
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0",
    # Firefox 3
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:63.0) Gecko/20100101 Firefox/63.0",
    # Microsoft Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134",
    # Opera
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36 OPR/56.0.3051.99",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/12.0.1 Safari/605.1.15",
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
