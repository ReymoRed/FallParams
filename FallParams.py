from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from bs4 import BeautifulSoup
from itertools import chain
from pathlib import Path
import urllib.request
import argparse
import json
import re
import os


def setup_argparser():
    """
    setup argparser Module

    :rtype: object
    """
    parser = argparse.ArgumentParser(prog='FallParams.py', usage='python3 %(prog)s [options]')
    parser.add_argument('-u', type=str,
                        help='Enter a url to retrieve the parameters')
    return parser


def is_valid_domain(domain):
    """
    returns domain is valid or not (by regex)

    :rtype: bool
    """
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, domain) is not None


def is_live_domain(domain):
    """
    returns domain is live or not (by request to the domain)

    :rtype: bool
    """
    return True if 400 > urllib.request.urlopen(domain).getcode() >= 200 else False


def get_inputs_names_and_ids(inputs):
    """
    returns Names and ID's of Inputs

    :param inputs:
    :return set(names_and_ids):
    """
    names_and_ids = set(chain.from_iterable([[inp.get('name'), inp.get('id')] for inp in inputs]))
    return set(filter(None, names_and_ids))


def get_href_params(a_tags):
    """
    returns href of <a> tags in the page

    :param a_tags:
    :type a_tags: BeautifulSoup
    :return: merged_params
    :rtype: set
    """
    params = [parse_qs(urlparse(a.get('href')).query).keys() for a in a_tags]
    merged_params = set(chain.from_iterable([list(param) for param in params]))
    return set(filter(None, merged_params))


def get_scripts_variables(page_source):
    """
    returns <script> tags variables

    :rtype: set
    """
    p = re.compile('var (\w+|\d+)')
    parsed_variables = p.findall(page_source)
    filtered_parsed_variables = [item for item in parsed_variables if len(item) > 1]
    #### We are filtering lower than 1 length Variables
    return set(filter(None, filtered_parsed_variables))


def get_multilevel_jsons_keys(soup):
    """
    returns Two tuple of sets

    note: if the expected part occurs, the sets will be None

    :rtype: (set, set)
    """
    try:
        scripts_content = set(json.loads(soup.find('script', type='application/json').text).keys())
        multi_level_jsons = set(chain.from_iterable(
            [list(item.keys()) for item in list(scripts_content.values()) if type(item) is dict]))
        return scripts_content, multi_level_jsons
    except:
        return set(), set()


def setup_selenium():
    """
    returns Chrome Web Driver (headless) with basic options

    :rtype: ChromeDriverManager
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver


def parameters_extractor(domain):
    """
    return chain of parameters in the page

    :param domain:
    :return chain:
    """
    driver = setup_selenium()
    driver.get(domain)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    inputs = soup.find_all('input')
    a_tags = soup.find_all('a')

    inputs_keys = get_inputs_names_and_ids(inputs)
    queries = get_href_params(a_tags)
    valid_parsed = get_scripts_variables(driver.page_source)
    scripts_content, multi_level_jsons = get_multilevel_jsons_keys(soup)
    driver.close()

    return chain(inputs_keys, queries, valid_parsed, scripts_content, multi_level_jsons)


def validator(domain):
    """
    call is_valid_domain() and is_live_domain()
    and check domain status

    :rtype: bool
    """
    if not is_valid_domain(domain):
        print("URL is Wrong!")

    if not is_live_domain(domain):
        print("URL isn't Live!")


def check_folder_file(url):
    """
    If the path output/ does not exist, it creates it
    and also if the file (domain+.txt) does not exist, it creates it

    :rtype: Path
    """
    #### Check/Create folder Output
    output_folder = dir_path + '/output/'
    os.makedirs(output_folder, exist_ok=True)

    #### Check/Create file by domain name
    domain = str(urlparse(url).netloc)
    path = Path(f'{output_folder}{domain}.txt')
    path.touch(exist_ok=True)

    return path


def main():
    validator(args.u)
    values = parameters_extractor(args.u)
    if values:
        file_path = check_folder_file(args.u)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines('\n'.join(values))
        print(f'Done! Check the file path: {file_path}')
    else:
        print('No parameters found!')


if __name__ == '__main__':
    args = setup_argparser().parse_args()
    dir_path = os.path.abspath(os.path.dirname(__file__))
    main()
