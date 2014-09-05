import os
import logging
import getpass
import ConfigParser


class Configuration():

    def __init__(self,):

        # centinel user
        self.current_user  = getpass.getuser()
        user_home          = os.path.expanduser('~' + self.current_user)
        self.centinel_home = os.path.join(user_home, '.centinel')

        # directory structure
        self.experiments_dir = os.path.join(os.path.dirname(__file__),
                                            "experiments")
        self.data_dir        = os.path.join(os.path.dirname(__file__),
                                            "data")
        self.results_dir     = os.path.join(self.centinel_home, 'results')

        # logging
        self.log_level  = logging.INFO
        self.log_file   = None
        # an alternative is os.path.join(centinel_home,
        # "centinel.log")
        self.log_format = '%(levelname)s: %(message)s'

        # server
        self.server_url = "http://127.0.0.1:5000"
        self.login_file = os.path.join(self.centinel_home, 'login')

        # proxy
        self.proxy_type = None  # "socks" or "http"
        self.proxy_url  = None  # "http://127.0.0.1:9050"
        self.proxy_type = None
        if self.proxy_type:
            self.proxy  = {self.proxy_type: self.proxy_url}

    def parse_config(self, config_file):
        """Given a configuration file, read in and interpret the results"""

        config = ConfigParser.RawConfigParser()
        config.read(config_file)

        # centinel user
        self.current_user  = config.get("user_info", "current_user")
        self.centinel_home = config.get("user_info", "centinel_home")

        # directory structure
        self.experiments_dir = config.get("dirs", "experiments")
        self.data_dir        = config.get("dirs", "data")
        self.results_dir     = config.get("dirs", "results")

        # logging
        # treat the log level as an int
        self.log_level  = config.getint("logs", "log_level")
        self.log_file   = config.get("logs", "log_file")
        # Note: if this changes in the future, ensure that we are
        # still getting raw input, not interpolated (variable insertion)
        self.log_format = config.get("logs", "log_format")

        # server
        self.server_url = config.get("server", "server_url")
        self.login_file = config.get("server", "login_file")

        # proxy
        self.proxy_type = config.get("proxy", "proxy_type")
        self.proxy_url = config.get("proxy", "proxy_url")
        self.proxy_type = None
        if self.proxy_type:
            self.proxy  = {self.proxy_type: self.proxy_url}

    def write_out_config(self, config_file):
        """Write out the configuration file

        Note: this will erase all comments from the config file

        """
        config = ConfigParser.RawConfigParser()

        # centinel user
        config.add_section("user_info")
        config.set("user_info", "current_user", self.current_user)
        config.set("user_info", "centinel_home", self.centinel_home)

        # directory structure
        config.add_section("dirs")
        config.set("dirs", "experiments", self.experiments_dir)
        config.set("dirs", "data", self.data_dir)
        config.set("dirs", "results", self.results_dir)

        # logging
        config.add_section("logs")
        config.set("logs", "log_level", self.log_level)
        config.set("logs", "log_file", self.log_file)
        config.set("logs", "log_format", self.log_format)

        # server
        config.add_section("server")
        config.set("server", "server_url", self.server_url)
        config.set("server", "login_file", self.login_file)

        # proxy
        config.add_section("proxy")
        config.set("proxy", "proxy_type", self.proxy_type)
        config.set("proxy", "proxy_url", self.proxy_url)

        with open(config_file, 'w') as f:
            config.write(f)
