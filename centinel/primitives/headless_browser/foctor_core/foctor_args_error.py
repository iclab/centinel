__author__ = 'rishabn'


def fp_crawler_mode_error():
    str_err = "Please specify a crawl mode: standard, tor, search_log, or login_log \n"
    str_err += "python front-page-crawler.py <crawl-mode>"
    print str_err
    raise SystemExit


def fp_crawler_standard_mode_error():
    str_err = "Usage for standard crawl: python front-page-crawler.py standard <site-list> <start-index> "
    str_err += "<end-index> <capture-path> <display 0/1> <process-tag>"
    print str_err
    raise SystemExit


def fp_crawler_tor_mode_error():
    str_err = "Usage for tor crawl: python front-page-crawler.py tor <site-list> <start-index> "
    str_err += "<end-index> <capture-path> <display 0/1> <process-tag> <exit-ip> <tor-port>"
    print str_err
    raise SystemExit


def fp_crawler_search_mode_error():
    str_err = "Usage for search-log crawl: python front-page-crawler.py search_log <site-list> <start-index> "
    str_err += "<end-index> <capture-path> <display 0/1> <process-tag> <output-rule-log>"
    print str_err
    raise SystemExit


def fp_crawler_login_mode_error():
    str_err = "Usage for login-log crawl: python front-page-crawler.py login_log <site-list> <start-index> "
    str_err += "<end-index> <capture-path> <display 0/1> <process-tag>"
    print str_err
    raise SystemExit


def search_crawler_mode_error():
    str_err = "Please specify a search crawl mode: generate rules (rule-gen), " \
              "search from existing rules (search-tor/search-standard)"
    str_err += "\npython search-crawler.py <search-crawl-mode>"
    print str_err
    raise SystemExit


def search_crawler_gen_rules_error():
    str_err = "Usage for search-log crawl: python search-crawler.py rule-gen <site-list> <start-index> "
    str_err += "<end-index> <capture-path> <display 0/1> <process-tag> <output-rule-log>"
    print str_err
    raise SystemExit


def search_crawler_tor_mode_error():
    str_err = "Usage for search-log crawl: python search-crawler.py search-tor <rule-list> <start-index> "
    str_err += "<end-index> <capture-path> <display 0/1> <process-tag> <exit-ip> <tor-port>"
    print str_err
    raise SystemExit


def search_crawler_standard_mode_error():
    str_err = "Usage for search-log crawl: python search-crawler.py search-standard <rule-list> <start-index> "
    str_err += "<end-index> <capture-path> <display 0/1> <process-tag>"
    print str_err
    raise SystemExit


def login_crawler_mode_error():
    str_err = "Please specify a login crawl mode: generate rules (rule-gen), " \
              "search from existing rules (login-tor/login-standard)"
    str_err += "\npython login-crawler.py <login-crawl-mode>"
    print str_err
    raise SystemExit


def login_crawler_compatible_sites_error():
    str_err = "Usage for login crawl: python login-crawler.py login-standard <site-list> <credentials-file> "
    str_err += "<start-index> <end-index> <capture-path> <display 0/1> <process-tag>"
    print str_err
    raise SystemExit


def login_crawler_gen_rules_error():
    str_err = "Usage for login crawl: python login-crawler.py rule-gen <credentials-file> <start-index> "
    str_err += "<end-index> <capture-path> <display 0/1> <process-tag> <output-rule-log>"
    print str_err
    raise SystemExit


def login_crawler_standard_playback_error():
    str_err = "Usage for login crawl: python login-crawler.py standard-playback <rule-list> <credentials-file> " \
              "<start-index> <end-index> <capture-path> <display 0/1> <process-tag>"
    print str_err
    raise SystemExit


def login_crawler_tor_playback_error():
    str_err = "Usage for login crawl: python login-crawler.py tor-playback <rule-list> <credentials-file> " \
              "<start-index> <end-index> <capture-path> <display 0/1> <process-tag> <exit-ip> <tor-port>"
    print str_err
    raise SystemExit


