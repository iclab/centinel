__author__ = 'xinwenwang'


class Bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''


def ic_assert(self, assert_name, expr, result):
        try:
            self.__getattribute__(assert_name)(expr)
            print Bcolors.OKGREEN + '%s passed' %(result['domain']) + Bcolors.ENDC
        except AssertionError as err:
            err_msg = 'unknown error, no message given' if result['error'] is '' else result['error']
            self.error_list[result['domain']] = err_msg


def echo_err(err_list):
    for err in err_list:
        print Bcolors.FAIL + '%s %s' % (err, err_list[err]) + Bcolors.ENDC
    raise AssertionError('%s errors found' % (len(err_list)))