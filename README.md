# Welcome to the sluguscripts repo!

This repo includes the code for the University of California, Santa Cruz Astronomy department's daily [arXiv astro-ph](https://arxiv.org/archive/astro-ph) mailer, **sluguscripts**. We thank the Astronomy graduate students at the University of Arizona for the inspiration - this repo is forked from theirs, which you can view [here](https://github.com/ua-astro-grads/arxiv-mailer).

UCSC Contributors: Courtney Carreira, Diego Garza, Anavi Uppal, Rishank Diwan

## Getting started

To run this arXiv mailer, there are three primary stages:
1. Build your department directory by scraping a publicly-available URL.
2. Cross-match each day's astro-ph posts with your department directory to find which arXiv posts include members of your department.
3. Generate and send an email every day (or week - info below!).

### Virtual environment

This entire repo should be run within a Python virtual environment. Use the above `requirements.txt` file to set up that environment as follows:
```
python3 -m venv .mailer-venv
source .mailer-venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

### Setting up `config.py`

In order to send the emails, you'll need to set up the email username, password, and other credentials. For security reasons, these credentials should **not** be pushed to a GitHub repo. Instead, copy `config.py.template`, change the filename, and edit the credentials there. The `.gitignore` file will not push any `config.py` files.

```
cp config.py.template config.py
```

Then, share your `config.py` file internally with your team.

For sluguscripts, we set up a Gmail account and Google Groups to build our email list. Each institution will have a different way of doing this, if I had to guess. With a Gmail account, you set up a Gmail SMTP password by turning on 2-Factor Authentication and then creating an "App password" in the Google Account settings. More information about this process can be found [here](https://support.google.com/mail/answer/185833?hl=en).

### Main file: `mailer.py`

All of the magic happens in `mailer.py`. We've copied the following overview of what this file does from [StewarXiv](https://github.com/ua-astro-grads/arxiv-mailer), with a few UofA&rarr;UCSC modifications:

> Here's what the script does:
> 
> 1. Build the personnel directory from the department website, using `build_directory`. If you've ever done web scraping before, it is straightforward code, but (as long as it's working) not important exactly how it accomplishes that. It grabs names (used as a dict key in the form (last_name, first_names)) and headshot ('image').
> 
> 2. Fetch the arXiv RSS feed and filter it (`get_matching_posts`). The (maybe confusingly named) `unpack_feed_entry` function returns `None` when there is not enough evidence that this is UCSC people.

>    - This is where it gets a little hairy: `approximate_name_lookup` gives a score of 0, 1, or 2 based on the criteria commented there.
>    - If a score of 1 or greater is found, it goes to inspect the evidence. `gather_affiliation_evidence` retrieves the LaTeX source of the arXiv posting. It does a case-insensitive search through the whole text for some institution names and domains (see UCSC_RE) and counts the matches as an evidence score. This can push a first initial-last name match over the threshold for inclusion, or skip a posting if none of those strings appear anywhere in the TeX source (you'd expect at least 'santa cruz' to appear somewhere!).
> 
> 3. Generate the email:
> 
>    - The `render_mailing` function takes a "context" dictionary, and uses Jinja2 (a text templating language) to generate the mailing from snippets of text or HTML in the .jinja2.html files.
>    - The `compose_email` function attaches the addresses, HTML and text versions of the email, and the subject line to an EmailMessage object the Python stdlib mail support knows how to send.
> 
> 4. Send the email: The script reads environment variables `$MAIL_SERVER`, `$MAIL_PORT`, `$MAIL_USERNAME`, and `$MAIL_PASSWORD` from `config.py`.

We've added several command-line flags via `argparse` to `mailer.py`, as follows:
| Argument | Format | Description | Default |
| -------- | ------ | ----------- | ------- |
| `--skip_new_directory` | `store_true` | Skips new directory build and instead uses existing `directory.pickle` file. | False |
| `--weekly_email` | `store_true` | If desired, switch mailer to weekly email compiling all of the week's papers into one email sent on Friday. | False |
| `--debug` | `store_true` | While debugging the actual email generation, will save local file verions, will NOT send emails to the real email list. | False |
| `--mail_test` | `store_true` | Will send test emails. | False |
| `-v`, `--verbose` | `store_true` | Prints helpful information to the screen. | False |

Additionally, we've implemented a way to record known name alternatives that aren't otherwise code-able. For example, if someone is named Andrew, but sometimes publishes as Andy, there's basically no clean way to identify that algorithmically. As such, you can manually add names to `known_name_alternatives.json` which `mailer.py` will check against the arXiv posts' author lists. In this file, all names (first and last) must be *caseless* and all acceptable first names must be listed.

If this code were being modified for a different department, most of your time would be spent modifying `build_directory` to suit the HTML set-up of your department's directory page.


### Running `mailer.py` automatically, every day

Feel free to use any of your favorite scheduling tool to run the python script automatically at a regular cadence. For our deployment, we use [crontab](https://man7.org/linux/man-pages/man5/crontab.5.html) on an iMac connected to the internet via ethernet. We have setup the crontab job to run at 9:35AM every morning on Mondays, Tuesdays, Wednesdays, Thursdays and Fridays, which looks like:

```
35 09 * * 1-5 bash /Users/sluguscripts/sluguscripts/run_pyemail.sh
```

where `run_pyemail.sh` takes the form

```
#!/bin/bash

sluguscript_cwd= # location of GitHub repo

cd $sluguscript_cwd

# create a log file from the bash job running this python script
# assumes logs_bash has been created as a directory in $sluguscript_cwd
logfile_suffix=$(date +"%Y_%m_%d")
logfile=$sluguscript_cwd"/logs_bash/py_mailer_info_"$logfile_suffix".log"

pyvenv=.mailer-venv"/bin/activate"

source $pyvenv

pyscript=$sluguscript_cwd"/mailer.py"

python3 $pyscript --verbose >> $logfile 2>&1

deactivate
```

The iMac being used is frequently either shutdown or in sleep mode. We use the power management utility [pmset](https://en.wikipedia.org/wiki/Pmset) to turn on the computer, run the script, and place the computer back in sleep mode.


## Known issues

Here, we compile a list of known issues or shortcomings that we have not solved. Some are not solveable, just choices we made when confronted with an edge case, but some could be fixed with more effort/attention.

* To gather evidence of department affiliation for any astro-ph post, `mailer.py` searchs through the TeX source from the arXiv posting. However, not every author uploads the TeX source. In that case, `mailer.py` relies on how closely the author names match how the department members are listed in the directory. If there is no TeX source to check affiliations and all possible author matches are listed by first intials-only (i.e., J. Doe), we consider that insufficient evidence and do not include that post in the email.
* Conventionally, many Hispanic people have two last names, so they may publish under each last name interchangeably. We have added some support for this within `approximate_name_lookup` in `mailer.py`, but admittedly, it's not perfect.