import pytest
from centinel.primitives.headless_browser import HeadlessBrowser
import os
import sys
from subprocess import call

class TestHeadlessbrowser:

    def test_files_exist_URL(self):
        """
        test if all the files (HAR file, screenshot, html and json file)
        generated for a URL
        """
        hb = HeadlessBrowser()
        call(["rm", "-rf", "har", "htmls", "screenshots", "hb_results.json"])
        URL = "www.google.com"
        hb.run(url=URL)

        if URL[-1] == "/":
            path = URL.split('/')[-2]
        else:
            path = URL.split('/')[-1]
        URL = URL.split('/')[0]

        # assert if har file is generated
        assert True == os.path.exists('./har/')
        length = len([name for name in os.listdir('./har/') if name.endswith(".har") and name.startswith(URL)])
        assert length == 1

        # assert if html page is generated
        assert True == os.path.exists('./htmls/')
        length = len([name for name in os.listdir('./htmls/') if name.endswith(".html")])
        assert length == 1
        file_name = './htmls/' + path + '.html'
        assert os.path.isfile(file_name)
        assert os.stat(file_name).st_size != 0

        # assert if sceenshot is generated
        assert True == os.path.exists('./screenshots/')
        length = len([name for name in os.listdir('./screenshots/') if name.endswith(".png")])
        assert length == 1
        file_name = './screenshots/' + path + '.png'
        assert os.path.isfile(file_name)
        assert os.stat(file_name).st_size != 0

        # assert if json file is generated
        assert True == os.path.exists('./hb_results.json')
        assert os.stat('./hb_results.json').st_size != 0

        call(["rm", "-rf", "har", "htmls", "screenshots", "hb_results.json"])


    def test_files_exist_URLs_file(self):
        """
        test if all the files (HAR file, screenshot, html and json file)
        generated for URLs in a file
        """
        hb = HeadlessBrowser()
        url_file = 'data/headless_browsing.txt'
        call(["rm", "-rf", "har", "htmls", "screenshots", "hb_results.json"])
        hb.run(input_files=url_file)

        # assert if /har folder is created
        assert True == os.path.exists('./har/')

        #assert if /htmls folder is created
        assert True == os.path.exists('./htmls/')

        # assert if /screenshots is craeted
        assert True == os.path.exists('./screenshots/')

        #assert if json file is generated
        assert True == os.path.exists('./hb_results.json')

        num_urls = sum(1 for line in open(url_file))

        length = len([name for name in os.listdir('./har/')])
        assert length == num_urls

        length = len([name for name in os.listdir('./htmls/')])
        assert length == num_urls

        length = len([name for name in os.listdir('./screenshots/')])
        assert length == num_urls

        urls = open(url_file, "r")
        tag = "1"
        for URL in urls:
            URL = URL.strip()
            index, url = URL.split(",")[0], URL.split(",")[1]
            url = url.strip()
            f_name = str(index) + "-" + tag

            if url[-1] == "/":
                path = url.split('/')[-2]
            else:
                path = url.split('/')[-1]
            url = url.split('/')[0]

            # assert if har file is generated for URL
            length = len([name for name in os.listdir('./har/') if name.endswith(".har") and name.startswith(url)])
            assert length == 1

            # assert if html page is generated for URL
            file_name = './htmls/' + f_name + '.html'
            assert os.path.isfile(file_name)
            assert os.stat(file_name).st_size != 0

            # assert if sceenshot is generated for URL
            file_name = './screenshots/' + f_name + '.png'
            assert os.path.isfile(file_name)
            assert os.stat(file_name).st_size != 0
            
        call(["rm", "-rf", "har", "htmls", "screenshots", "hb_results.json"])
        urls.close()

    
