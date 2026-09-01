#!/usr/bin/env python
import datetime
import time
import os
import os.path
import pickle
import re
import logging
import sys
import unicodedata
import smtplib
import ssl
from dateutil.parser import parse
from dateutil import tz
from bs4 import BeautifulSoup
import feedparser
import jinja2
import requests
import tarfile
import io
import argparse
from pylatexenc.latex2text import LatexNodes2Text

from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid

# import global config variables
from config import *

HERE = os.path.dirname(__file__)

FACULTY = 1
POSTDOC = 2
STAFF = 2
STUDENT = 3

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
UCSC_RE = re.compile(r'(university of california, santa cruz|university of california observatories|ucsc\.edu|uco|uc santa cruz|lick observatory)', flags=re.IGNORECASE)

# https://stackoverflow.com/questions/33857698/sending-email-from-python-using-starttls
_DEFAULT_CIPHERS = (
    'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
    'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
    '!eNULL:!MD5'
)


#######################################
# Create command line argument parser
#######################################
def create_parser():

    #handle user input with argparse
    parser = argparse.ArgumentParser(
        description="Flags and options from user.")

    parser.add_argument('--skip_new_directory',
        dest='skip_new_directory',
        action='store_true',
        help='Skips new directory build and instead uses existing directory. (default: False)',
        default=False)

    parser.add_argument('--daily_email',
        dest='daily_email',
        action='store_true',
        help='If desired, switch mailer to daily email. (default: False)',
        default=False)

    parser.add_argument('--debug',
        dest='debug',
        action='store_true',
        help='While debugging the actual email generation, will save local file verions, will NOT send emails. (default: True)',
        default=True)

    parser.add_argument('--mail_test',
        dest='mail_test',
        action='store_true',
        help='Will send test emails. (default: False)',
        default=False)

    parser.add_argument('-v', '--verbose',
        dest='verbose',
        action='store_true',
        help='Print helpful information to the screen? (default: False)',
        default=False)

    return parser


#######################################
# soupify() function
#######################################
def soupify(url):
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        req = requests.get(url, verify=False, headers=headers)
    return BeautifulSoup(req.text, features="lxml")


#######################################
# normalize_caseless() function
#######################################
def normalize_caseless(text):
    text = re.sub(r'[^\w]', ' ', text)
    # thanks to https://stackoverflow.com/a/29247821
    text = unicodedata.normalize("NFKD", text.casefold())
    text = text.strip()
    return text


#######################################
# build_directory() function
#######################################
def build_directory():
    people = {}
    base_link = 'https://astronomy.ucsc.edu'

    people_page = soupify('https://astronomy.ucsc.edu/people/')
    # for facwrap in people_page.select('.item-body'): #'.section-item h-card wrap'):
    for title_section in people_page.select('.section-container.ucsc-block-directory.tiled-page'):
        for personwrap in title_section.select('.section-item.h-card.wrap'):
            #print(personwrap)

            #item_body = personwrap.select_one('.item_body')
            h1 = personwrap.select_one('h3')
            # print(h1)
            name = normalize_caseless(h1.select_one('.p-name').text.strip()).split(' ')
            # print(name)
            # print(firstname)
            # lastname  = h1.select_one('.field--name-field-az-lname').text.strip()
            # name = (firstname, lastname)
            back = " ".join(name[:-1])
            # print(back)
            name = (name[-1], back)
            # print(name)

            # retrieve link to individual page
            ind_page_link = personwrap.find_all('a', href=True)[0]['href']
            ind_page = soupify(base_link + ind_page_link)

            # get position
            # try:
            #     position = h1.select_one(".item-info list-renderer")#[0].text.replace('\n', '')
            #     print(position)
            # except Exception as e:
            #     log.warning(f"Failed to get position for {name}")
            #     continue
            # get image
            try:
                image = ind_page.select('.item-image.square-img.imgLiquid')[0].select_one('img')['src'] # base_link + ind_page.select('article')[0].select_one('img')['src']
            except Exception as e:
                log.warning(f"Unable to find image for {name}")
                image = None

            people[name]= {
                # 'role': FACULTY,
                # 'position': position,
                'image': image, 
                # 'page': base_link + ind_page_link,
            }

    # postdoc_page = soupify('https://astronomy.ucsc.edu/people/#postdoc')
    # for wrap in postdoc_page.select('.card-body'):
    #     name = tuple(wrap.select('h3')[0].text.replace('\n', '').split(' ', 1))
    #     name = tuple(normalize_caseless(part.strip()) for part in name)[::-1] # lower case and reverse order

    #     # retrieve link to individual page
    #     ind_page_link = wrap.find_all('a', href=True)[0]['href']
    #     ind_page = soupify(base_link + ind_page_link)

    #     # get position
    #     try:
    #         position = ind_page.find_all("div", class_="field--name-field-az-titles")[0].text.replace('\n', '')
    #     except Exception as e:
    #         logger.warning(f"Failed to get position for {name}")
    #         continue
        
    #     # get image
    #     try:
    #         image = base_link + ind_page.select('article')[0].select_one('img')['src']
    #     except Exception as e:
    #         logger.warning(f"Unable to find image for {name}")
    #         image = None

    #     people[name]= {
    #         'role': POSTDOC,
    #         'position': position,
    #         'image': image,
    #         'page': base_link + ind_page_link,
    #     }

    # student_page = soupify('https://astronomy.ucsc.edu/people/#grads')
    # for wrap in student_page.select('.card-body'):

    #     h1 = wrap.select_one('h1')
    #     firstname = h1.select_one('.field--name-field-az-fname').text.strip()
    #     lastname  = h1.select_one('.field--name-field-az-lname').text.strip()
    #     name = (firstname, lastname)
    #     name = tuple(normalize_caseless(part.strip()) for part in name)[::-1]

    #     # retrieve link to individual page
    #     ind_page_link = wrap.find_all('a', href=True)[0]['href']
    #     ind_page = soupify(base_link + ind_page_link)

    #     # get image
    #     try:
    #         image = base_link + ind_page.select('article')[0].select_one('img')['src']
    #     except Exception as e:
    #         logger.warning(f"Unable to find image for {name}")
    #         image = None

    #     people[name]= {
    #         'role': STUDENT,
    #         'position': 'Graduate Student',
    #         'image': image,
    #         'page': base_link + ind_page_link,
    #     }

    # staff_page = soupify('https://astro.arizona.edu/people/staff')
    # for wrap in staff_page.select('.card-body'):

    #     h1 = wrap.select_one('h1')
    #     firstname = h1.select_one('.field--name-field-az-fname').text.strip()
    #     lastname  = h1.select_one('.field--name-field-az-lname').text.strip()
    #     name = (firstname, lastname)
    #     name = tuple(normalize_caseless(part.strip()) for part in name)[::-1]

    #     # retrieve link to individual page
    #     ind_page_link = wrap.find_all('a', href=True)[0]['href']
    #     ind_page = soupify(base_link + ind_page_link)

    #     # get image
    #     try:
    #         image = base_link + ind_page.select('article')[0].select_one('img')['src']
    #     except Exception as e:
    #         logger.warning(f"Unable to find image for {name}")
    #         image = None

    #     people[name]= {
    #         'role': STAFF,
    #         'position': 'Staff',
    #         'image': image,
    #         'page': base_link + ind_page_link,
    #     }

    # print("finished building directory")

    return people


#######################################
# test_name_regex() function
#######################################
NAME_RE = re.compile(r'^(?P<first>(?:(?P<initial>\w).*)[\. ]+)+(?P<last>\w.*)$')
def test_name_regex():
    assert NAME_RE.match('J.Long').groupdict() == {'first': 'J.', 'initial': 'J', 'last': 'Long'}
    assert NAME_RE.match('Joseph D. Long').groupdict() == {'first': 'Joseph D. ', 'initial': 'J', 'last': 'Long'}
    assert NAME_RE.match('J. D. Long').groupdict() == {'first': 'J. D. ', 'initial': 'J', 'last': 'Long'}
    assert NAME_RE.match('J Long').groupdict() == {'first': 'J ', 'initial': 'J', 'last': 'Long'}


#######################################
# test_initial_regex() function
#######################################
INITIAL_RE = re.compile(r'^\w(\.|\s|$)')
def test_initial_regex():
    assert INITIAL_RE.match('J. D.')
    assert not INITIAL_RE.match('Jo. D.')
    assert INITIAL_RE.match('J.D.')
    assert INITIAL_RE.match('J')
    assert INITIAL_RE.match('J D')


#######################################
# strip_initials() function and test_strip_initials() function
#######################################
ALL_INITIALS_RE = re.compile(r'\b\w\.?\s')
def strip_initials(names):
    return ' '.join(ALL_INITIALS_RE.sub('', names).split())
def test_strip_initials():
    assert strip_initials('J. Long') == 'Long'


#######################################
# approximate_name_lookup() function
#######################################
def approximate_name_lookup(name, people):
    # normalize at input boundary so comparisons are simply ==
    normalized_name = normalize_caseless(name)
    name_match = NAME_RE.match(normalized_name)
    if not name_match:
        logger.warning(f"Unable to parse {normalized_name=} with regex")
        return None, 0
    parts = name_match.groupdict()
    first_names = parts['first'].strip()
    first_initial = parts['initial']
    last_name = parts['last'].strip()

    for person_last, person_first in people:
        score = 0
        if person_last == last_name:
            # last name matches, but what about first?
            if person_first == first_names:
                # easy: last name matches, first name(s) match
                score = 2
            elif first_names.startswith(person_first):
                score = 2
            elif first_names != first_initial and first_names in person_first:
                # first_names is a substring of person_first
                # does person_first match after removing initials?
                if strip_initials(first_names).startswith(person_first):
                    score = 2
            elif person_first in first_names:
                # does first_names match after removing initials?
                if strip_initials(first_names).startswith(person_first):
                    score = 2
            elif person_first[0] == first_initial[0]:
                # harder: last name matches, first initial matches
                # check if it's an initial (single letter followed by space, period, or end of string
                re_match = INITIAL_RE.match(first_names)
                if re_match:
                    score = 1
                # otherwise, same first initial, different first name, so no match
            # else: same last name, different first name, no match
        if score:
            return (person_last, person_first), score
    return None, 0


#######################################
# test_approximate_name_lookup() function
#######################################
def test_approximate_name_lookup():
    people = {
        ('dave', 'a. bob c.'): None,
        ('ferris', 'edgar'): None,
        ('hausschuh', 'georgina'): None,
        ('rodrigo', 'marco navarro'): None
    }
    assert approximate_name_lookup('edgar ferris', people) == (('ferris', 'edgar'), 2)
    assert approximate_name_lookup('bob dave', people) == (('dave', 'a. bob c.'), 2)
    assert approximate_name_lookup('G. Hausschuh', people) == (('hausschuh', 'georgina'), 1)
    assert approximate_name_lookup('{M. Navarro Rodrigo}', people) == (('rodrigo', 'marco navarro'), 1)


#######################################
# evidence_in_texfile() function
#######################################
def evidence_in_texfile(fh):
    evidence = 0
    for line in fh:
        line = line.decode('utf8')
        if line[0] == '%':
            continue
        matches = UCSC_RE.findall(line)
        evidence += len(matches)
    return evidence


#######################################
# gather_affiliation_evidence() function
#######################################
def gather_affiliation_evidence(arxiv_id):
    url = f'https://arxiv.org/e-print/{arxiv_id}'
    evidence = 0
    gather_success = False
    try:
        logger.debug(f"Gathering evidence from {url}")
        res = requests.get(url, headers=headers)
        buff = io.BytesIO(res.content)
        archive = tarfile.open(fileobj=buff)
        texfiles = [m for m in archive.getmembers() if m.name.lower().endswith('.tex')]
        for info in texfiles:
            fh = archive.extractfile(info)
            evidence += evidence_in_texfile(fh)
        gather_success = True
        logger.info(f'Found {evidence=} for {arxiv_id=}')
    except Exception as e:
        logger.debug(e)
    return evidence, gather_success


#######################################
# unpack_feed_entry() function
#######################################
def unpack_feed_entry(post, people):

    #pull quick information
    title = post.title
    arxiv_area = post.tags[0]['term']

    #create author list
    #new arXiv RSS feed has a comma-separated author list instead of the a tag
    author_names = [author.strip() for author in
        BeautifulSoup(post.author, features="lxml").text.split(',')]
    authors = [(LatexNodes2Text().latex_to_text(name), approximate_name_lookup(name, people)) for name in author_names]

    #get publication date
    pub_date = str(post.published).split(' ')[:4]

    our_people_score = sum(item[1][1] for item in authors)
    if our_people_score < 1:
        return
    else:
        logger.info(f"Found {our_people_score=} from {authors=}")

    arxiv_id = post.link.rsplit('/', 1)[1]
    evidence, gather_success = gather_affiliation_evidence(arxiv_id)
    if gather_success and evidence == 0:
        logger.debug(f'Skipping {arxiv_id=} for lack of evidence: {our_people_score=} {evidence=}')
        return  # no matches to UCSC_RE
    elif not gather_success and our_people_score < 2:
        return  # could be two partial matches

    #the summary now also contains the arXiv ID and the type of posting (e.g. new, replacement) - just grab the abstract
    summary = BeautifulSoup(post.summary, features="lxml").text
    abstract = summary.split('Abstract: ')[-1]
    out = {
        'authors': authors,
        'title': title,
        'area': arxiv_area,
        'abstract': abstract.replace('\n', ' '),
        'arxiv_id': arxiv_id,
        'html_arxiv_id': post.id.rsplit(':', 1)[1],
        'pub_date': " ".join(pub_date),
    }

    return out


#######################################
# get_matching_posts() function
#######################################
def get_matching_posts(people):
    feed = feedparser.parse('https://rss.arxiv.org/rss/astro-ph')
    posts = []
    all_authors = []
    update_day = parse(feed.feed['updated']).astimezone(datetime.timezone.utc).date() #- datetime.timedelta(days=12) 
    pub_day = parse(feed.feed['published']).astimezone(datetime.timezone.utc).date() #- datetime.timedelta(days=12) 
    today = datetime.datetime.now(datetime.timezone.utc).date() #- datetime.timedelta(days=12) 
    if (update_day - today).days != 0:
        logger.warning(f"Mailer was invoked but feed was last updated on {update_day} UTC")
        sys.exit(1) # NEEDS TO BE COMMENTED OUT FOR TESTING
    if (pub_day - today).days != 0:
        logger.warning(f"Mailer was invoked but content in feed was last " +
                 f"published on {pub_day} UTC")
        sys.exit(1) # NEEDS TO BE COMMENTED OUT FOR TESTING
    for post in feed.entries:
        unpacked_post = unpack_feed_entry(post, people)
        if unpacked_post:
            posts.append(unpacked_post)
            for author in unpacked_post['authors']:
                if author[1][0] is not None:
                    key = author[1][0]
                    all_authors.append((key, people[key]))
    # sorting by the key, so by last names
    all_authors.sort()
    all_authors = [x[1] for x in all_authors]

    return posts, all_authors


#######################################
# render_mailing() function
#######################################
env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    autoescape=jinja2.select_autoescape(['html', 'xml'])
)
def render_mailing(context_dict):
    html_template = env.get_template('mailing.jinja2.html')
    html_mailing = html_template.render(**context_dict)
    text_template = env.get_template('mailing.jinja2.txt')
    text_mailing = text_template.render(**context_dict)

    return html_mailing, text_mailing


#######################################
# compose_email() function
#######################################
def compose_email(from_address, to_addresses, subject, html_mailing, text_mailing,
    cc_addresses=None):

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = to_addresses
    if cc_addresses:
        msg['CC'] = cc_addresses
    msg.set_content(text_mailing)
    msg.add_alternative(html_mailing, subtype='html')

    return msg


#######################################
# send_email() function
#######################################
def send_email(msg):
    host = MAIL_SERVER
    port = int(MAIL_PORT)
    user = MAIL_USERNAME
    password = MAIL_PASSWORD

    # only TLSv1 or higher
    context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3

    context.set_ciphers(_DEFAULT_CIPHERS)
    context.set_default_verify_paths()
    context.verify_mode = ssl.CERT_REQUIRED
    smtp_server = smtplib.SMTP_SSL(host, port=port, context=context)
    smtp_server.login(user, password)
    smtp_server.send_message(msg)


#######################################
# main() function
#######################################
def main():

    #begin timer
    time_global_start = time.time()

    #create the command line argument parser
    parser = create_parser()

    #store the command line arguments
    args = parser.parse_args()

    #print command line arguments
    if args.verbose:
        print(f"args.skip_new_directory  {args.skip_new_directory}")
        print(f"args.daily_email         {args.daily_email}")
        print(f"args.debug               {args.debug}")
        print(f"args.mail_test           {args.mail_test}")

    #set local time information
    run_time = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
    tzmst = tz.gettz('America/Los Angeles')
    run_time_local = run_time.astimezone(tzmst)
    day_of_week = run_time_local.strftime('%A')

    # if len(sys.argv) > 1:
    #     args = sys.argv[1:]
    #     if '-d' in args:
    #         DEMO_MODE = True

    #generate department directory
    if os.path.exists('./directory.pickle') and (args.skip_new_directory==True):
        with open('./directory.pickle', 'rb') as f:
            directory_to_pickle = pickle.load(f)
            people = directory_to_pickle['people']
    else:
        people = build_directory()
        directory_to_pickle = {'people': people, 'updated': run_time_local.strftime('%Y-%m-%d %H:%M %Z')}
        with open('./directory.pickle', 'wb') as f:
            pickle.dump(directory_to_pickle, f)

    posts, all_authors = get_matching_posts(people)

    context = context = {
            'people': people,
            'posts': posts,
            'all_authors': all_authors,
            'run_time': run_time_local.strftime('%Y-%m-%d %H:%M %Z'),
            'day_of_week': day_of_week,
            }

    # if DEMO_MODE and os.path.exists('./demo.pickle'):
    #     with open('./demo.pickle', 'rb') as f:
    #         context = pickle.load(f)
    #         # define locals from pickle
    #         people = context['people']
    #         posts = context['posts']
    #         all_authors = context['all_authors']
    #         # except run_time, update that in loaded dict
    #         context['run_time'] = run_time_local.strftime('%Y-%m-%d %H:%M %Z')
    #         context['day_of_week'] = day_of_week
    # if True: #else:
        # # people = build_directory()
        # # print(people)
        # context = {
        #     'people': people,
        #     'posts': posts,
        #     'all_authors': all_authors,
        #     'run_time': run_time_local.strftime('%Y-%m-%d %H:%M %Z'),
        #     'day_of_week': day_of_week,
        # }
        # if DEMO_MODE:
        #     with open('./demo.pickle', 'wb') as f:
        #         pickle.dump(context, f)

    #generate HTML and text versions of mailer email
    html_mailing, text_mailing = render_mailing(context)

    #if debugging, save HTML and text versions to view
    if args.debug:
        with open(os.path.join(HERE, f"mailing_{run_time_local.strftime('%Y_%m_%d')}.html"), 'w') as f:
            f.write(html_mailing)
        with open(os.path.join(HERE, f"mailing_{run_time_local.strftime('%Y_%m_%d')}.txt"), 'w') as f:
            f.write(text_mailing)

    #generate email addresses, subject line, etc.
    #courtney: commenting all of this out for now, until we understand better what it's doing
    # from_addr_spec = MAIL_USERNAME if not DEMO_MODE else 'astro-stewarxiv@list.arizona.edu'
    # from_addr = Address("StewarXiv", addr_spec=from_addr_spec)
    # # decide who to send to depending on content or demoing
    # if not DEMO_MODE and len(posts) > 0:
    #     to_addrs = [] #[Address("StewarXiv", addr_spec=MAIL_SENDTO)]
    # else:
    #     to_addrs = [] #[Address("ADMIN", addr_spec=MAIL_USERNAME)]
    subject = f'Sluguscripts {day_of_week} update: {len(posts)} {"preprint" if len(posts) == 1 else "preprints"} from {len(all_authors)} {"colleague" if len(all_authors) == 1 else "colleagues"}'
    
    #compose the email (also CC the sender of the email)
    #courtney: line under here is placeholder
    from_addr, to_addrs = 'test@ucsc.edu', []
    msg = compose_email(from_addr, to_addrs, subject, html_mailing, text_mailing,
        cc_addresses=from_addr)

    if args.debug:
        with open(os.path.join(HERE, f"mailing_{run_time_local.strftime('%Y_%m_%d')}.eml"), 'wb') as f:
            f.write(bytes(msg))

    #send the email
    # send_email(msg)

    #end timer
    time_global_end = time.time()
    logger.info(f"Time to execute program: {time_global_end-time_global_start}s.")
    if args.verbose:
        print(f"Time to execute program: {time_global_end-time_global_start}s.")
        

#######################################
# Run the program
#######################################
if __name__=="__main__":

    #set log file
    logging.basicConfig(
        level=logging.DEBUG,                  
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",         
        filename=os.path.join(HERE, f'logs/{datetime.date.today()}.log'),                   
        filemode="w"                          #"w" overwrites file each run, "a" appends
    )
    logger = logging.getLogger(__name__)

    #run program
    main()
