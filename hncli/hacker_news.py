# -*- coding: utf-8 -*-

# Copyright 2015 Donne Martin. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from __future__ import print_function
from __future__ import division

import os
import re
import urllib
from urlparse import urlparse
import webbrowser
try:
    # Python 3
    import configparser
except ImportError:
    # Python 2
    import ConfigParser as configparser

import click
import requests

from .lib.haxor.haxor import HackerNewsApi, InvalidUserID
from .lib.html2text.html2text import HTML2Text
from .lib.pretty_date_time import pretty_date_time
from .onions import onions


class HackerNews(object):
    """Encapsulates Hacker News.

    Attributes:
        * COMMENT_INDENT: A string representing the indent amount for comments.
        * CONFIG: A string representing the config file name.
        * CONFIG_SECTION: A string representing the main config file section.
        * CONFIG_INDEX: A string representing the last index used.
        * MSG_ASK: A string representing the message displayed when the
            command hn ask is executed.
        * MSG_BEST: A string representing the message displayed when the
            command hn best is executed.
        * MSG_ITEM_NOT_FOUND: A string representing the message displayed when
            the given item is not found.
        * MSG_JOBS: A string representing the message displayed when the
            command hn jobs is executed.
        * MSG_NEW: A string representing the message displayed when the
            command hn new is executed.
        * MSG_ONION: A string representing the message displayed when the
            command hn onion is executed.
        * MSG_SHOW: A string representing the message displayed when the
            command hn show is executed.
        * MSG_TOP: A string representing the message displayed when the
            command hn top is executed.
        * MSG_SUBMISSIONS: A string representing the message displayed for
            repositories when the command hn user is executed.
        * hacker_news_api: An instance of HackerNews.
        * item_ids: A list containing the last set of ids the user has seen,
            which allows the user to quickly access an item with the
            gh view [#] [-u/--url] command.
        * QUERY_RECENT: A list representing the query to show recent comments.
        * TIP0, TIP1, TIP2: StringS that lets the user know about the
            hn view command.
        * URL_POST: A string that represents a Hacker News post minus the
            post id.
    """

    COMMENT_INDENT = '    '
    CONFIG = '.hncliconfig'
    CONFIG_SECTION = 'hncli'
    CONFIG_INDEX = 'item_ids'
    MSG_ASK = 'Ask HN'
    MSG_BEST = 'Best'
    MSG_ITEM_NOT_FOUND = 'Item with id {0} not found.'
    MSG_JOBS = 'Jobs'
    MSG_NEW = 'Latest'
    MSG_ONION = 'Top Onion'
    MSG_SHOW = 'Show HN'
    MSG_TOP = 'Top'
    MSG_SUBMISSIONS = 'User submissions:'
    QUERY_RECENT = 'minutes ago'
    TIP0 = 'Tip: View the page or comments for '
    TIP1 = ' with the following command:\n'
    TIP2 = '  hn view [#] [comment_filter] [-c] [-cr] [-b] - hn view --help'
    URL_POST = 'https://news.ycombinator.com/item?id='

    def __init__(self):
        """Initializes HackerNews.

        Args:
            * None.

        Returns:
            None.
        """
        self.hacker_news_api = HackerNewsApi()
        self.item_ids = []
        self.html_to_text = None
        self._init_html_to_text()

    def _config(self, config_file_name):
        """Gets the config file path.

        Args:
            * config_file_name: A String that represents the config file name.

        Returns:
            A string that represents the hn config file path.
        """
        home = os.path.abspath(os.environ.get('HOME', ''))
        config_file_path = os.path.join(home, config_file_name)
        return config_file_path

    def _init_html_to_text(self):
        """Initializes HTML2Text.

        Args:
            * None.

        Returns:
            None.
        """
        self.html_to_text = HTML2Text()
        self.html_to_text.body_width = 0
        self.html_to_text.ignore_images = False
        self.html_to_text.ignore_emphasis = False
        self.html_to_text.ignore_links = False
        self.html_to_text.skip_internal_links = False
        self.html_to_text.inline_links = False
        self.html_to_text.links_each_paragraph = False

    def ask(self, limit):
        """Displays Ask HN posts.

        Args:
            * limit: A int that specifies the number of items to show.
                Optional, defaults to 10.

        Returns:
            None.
        """
        self.print_items(
            message=self.headlines_message(self.MSG_ASK),
            item_ids=self.hacker_news_api.ask_stories(limit))

    def best(self, limit):
        """Displays best posts.

        Args:
            * limit: A int that specifies the number of items to show.
                Optional, defaults to 10.

        Returns:
            None.
        """
        self.print_items(
            message=self.headlines_message(self.MSG_BEST),
            item_ids=self.hacker_news_api.best_stories(limit))

    def format_markdown(self, text):
        """Adds color to the input markdown using click.style.

        Args:
            * text: A string that represents the markdown text.

        Returns:
            A string that has been colorized.
        """
        pattern_url_name = r'[^]]*'
        pattern_url_link = r'[^)]+'
        pattern_url = r'([!]*\[{0}]\(\s*{1}\s*\))'.format(
            pattern_url_name,
            pattern_url_link)
        regex_url = re.compile(pattern_url)
        text = regex_url.sub(click.style(r'\1', fg='green'), text)
        pattern_url_ref_name = r'[^]]*'
        pattern_url_ref_link = r'[^]]+'
        pattern_url_ref = r'([!]*\[{0}]\[\s*{1}\s*\])'.format(
            pattern_url_ref_name,
            pattern_url_ref_link)
        regex_url_ref = re.compile(pattern_url_ref)
        text = regex_url_ref.sub(click.style(r'\1', fg='green'), text)
        regex_list = re.compile(r'(  \*.*)')
        text = regex_list.sub(click.style(r'\1', fg='blue'), text)
        regex_header = re.compile(r'(#+) (.*)')
        text = regex_header.sub(click.style(r'\2', fg='yellow'), text)
        regex_bold = re.compile(r'(\*\*|__)(.*?)\1')
        text = regex_bold.sub(click.style(r'\2', fg='cyan'), text)
        regex_code = re.compile(r'(`)(.*?)\1')
        text = regex_code.sub(click.style(r'\1\2\1', fg='cyan'), text)
        text = re.sub(r'(\s*\r?\n\s*){2,}', r'\n\n', text)
        return text

    def comments(self, post_id, regex_query):
        """Views the comments for the given post_id.

        Args:
            * hacker_news: An instance of Hacker News.
            * post_id: An int representing the post's id.
            * regex_query: A string that specifies the regex query to match.
                Optional, defaults to ''.

        Returns:
            None.
        """
        try:
            item = self.hacker_news_api.get_item(post_id)
            self.print_comments(item, regex_query=regex_query)
        except InvalidItemID:
            self.print_item_not_found(post_id)

    def headlines_message(self, message):
        """Creates the "Fetching [message] Headlines..." string.

        Args:
            * message: A string that represents the message.

        Returns:
            A string: "Fetching [message] Headlines..."
        """
        return 'Fetching {0} Headlines...'.format(message)

    def hiring(self, regex_query, post_id):
        """Displays comments matching the monthly who is hiring post.

        Searches the monthly Hacker News who is hiring post for comments
        matching the given regex_query.  Defaults to searching the latest
        post based on your installed version of hncli.

        Args:
            * regex_query: A string that specifies the regex query to match.
            * id: An int that specifies the who is hiring post id.
                Optional, defaults to the latest post based on your installed
                version of hncli.

        Returns:
            None.
        """
        try:
            item = self.hacker_news_api.get_item(post_id)
            self.print_comments(item, regex_query)
        except InvalidItemID:
            self.print_item_not_found(post_id)

    def jobs(self, limit):
        """Displays job posts.

        Args:
            * limit: A int that specifies the number of items to show.
                Optional, defaults to 10.

        Returns:
            None.
        """
        self.print_items(
            message=self.headlines_message(self.MSG_JOBS),
            item_ids=self.hacker_news_api.job_stories(limit))

    def new(self, limit):
        """Displays the latest posts.

        Args:
            * limit: A int that specifies the number of items to show.
                Optional, defaults to 10.

        Returns:
            None.
        """
        self.print_items(
            message=self.headlines_message(self.MSG_NEW),
            item_ids=self.hacker_news_api.new_stories(limit))

    def onion(self, limit):
        """Displays onions.

        Args:
            * limit: A int that specifies the number of items to show.
                Optional, defaults to 50.

        Returns:
            None.
        """
        click.secho('\n' + self.headlines_message(self.MSG_ONION) + '\n',
                    fg='blue')
        index = 1
        for onion in onions[0:limit]:
            formatted_index_title = self.format_index_title(index, onion)
            click.echo(formatted_index_title)
            index += 1
        click.echo('')

    def print_comments(self, item, regex_query='', depth=0):
        """Recursively print comments and subcomments for the given item.

        Args:
            * item: An instance of haxor.Item.
            * regex_query: A string that specifies the regex query to match.
            * depth: The current recursion depth, used to indent the comment.

        Returns:
            None.
        """
        comment_ids = item.kids
        if item.text is not None:
            print_comment = True
            if regex_query and not self.regex_match(item, regex_query):
                print_comment = False
            formatted_heading, formatted_comment = self.format_comment(
                    item, depth)
            click.echo(formatted_heading)
            if print_comment:
                click.echo(formatted_comment)
        if not comment_ids:
            return
        for comment_id in comment_ids:
            try:
                comment = self.hacker_news_api.get_item(comment_id)
                depth += 1
                self.print_comments(comment,
                                    regex_query=regex_query,
                                    depth=depth)
                depth -= 1
            except InvalidItemID:
                self.print_item_not_found(comment_id)

    def format_comment(self, item, depth):
        """Formats a given item's comment.

        Args:
            * item: An instance of haxor.Item.
            * depth: The current recursion depth, used to indent the comment.

        Returns:
            A tuple of the following:
                * A string representing the formatted comment header.
                * A string representing the formatted comment.
        """
        indent = self.COMMENT_INDENT * depth
        formatted_heading = click.style(
            '\n' + indent + item.by + ' - ' +
            str(pretty_date_time(item.submission_time)) + '\n',
            fg='yellow')
        formatted_comment = click.wrap_text(
            text=item.text,
            initial_indent=indent,
            subsequent_indent=indent)
        return formatted_heading, formatted_comment

    def format_index_title(self, index, title):
        """Formats and item's index and title.

        Args:
            * index: An int that specifies the index for the given item.
            * title: A string that represents the item's title.

        Returns:
            A string representation of the formatted index and title.
        """
        space = '  ' if index < 10 else ' '
        formatted_index_title = click.style('  ' + str(index) + '.' + space,
                                            fg='magenta')
        formatted_index_title += click.style(title + ' ',
                                             fg='blue')
        return formatted_index_title

    def print_formatted_item(self, item, index):
        """Formats and prints an item.

        Args:
            * item: An instance of haxor.Item.
            * index: An int that specifies the index for the given item,
                used with the hn view [index] commend.

        Returns:
            None.
        """
        formatted_index_title = self.format_index_title(index, item.title)
        click.secho(formatted_index_title, nl=False)
        if item.url is not None:
            netloc = urlparse(item.url).netloc
            netloc = re.sub('www.', '', netloc)
            click.secho('(' + netloc + ')',
                        fg='magenta')
        else:
            click.echo('')
        click.secho('      ' + str(item.score) + ' points ',
                    nl=False,
                    fg='green')
        click.secho('by ' + item.by + ' ',
                    nl=False,
                    fg='yellow')
        click.secho(str(pretty_date_time(item.submission_time)) + ' ',
                    nl=False,
                    fg='cyan')
        num_comments = str(item.descendants) if item.descendants else '0'
        click.secho('| ' + num_comments + ' comments\n',
                    fg='green')
        self.item_ids.append(item.item_id)

    def format_item(self, item, index):
        """Formats an item.

        Args:
            * item: An instance of haxor.Item.
            * index: An int that specifies the index for the given item,
                used with the hn view [index] commend.

        Returns:
            A string representing the formatted item.
        """
        formatted_item = self.format_index_title(index, item.title)
        if item.url is not None:
            netloc = urlparse(item.url).netloc
            netloc = re.sub('www.', '', netloc)
            formatted_item += click.style('(' + netloc + ')',
                                          fg='magenta')
        formatted_item += '\n'
        formatted_item += click.style('      ' + str(item.score) + ' points ',
                                      fg='green')
        formatted_item += click.style('by ' + item.by + ' ',
                                      fg='yellow')
        formatted_item += click.style(
            str(pretty_date_time(item.submission_time)) + ' ',
            fg='cyan')
        num_comments = str(item.descendants) if item.descendants else '0'
        formatted_item += click.style('| ' + num_comments + ' comments\n',
                                      fg='green')
        self.item_ids.append(item.item_id)
        return formatted_item

    def print_item_not_found(self, item_id):
        """Prints a message the given item id was not found.

        Long description.

        Args:
            * item_id: An int representing the item id.

        Returns:
            None.
        """
        click.secho(self.MSG_ITEM_NOT_FOUND.format(item_id), fg='red')

    def print_items(self, message, item_ids):
        """Prints the items and headers with tabulate.

        Args:
            * message: A string to print out to the user before outputting
                the results.
            * item_ids: A collection of items to print as rows with tabulate.
                Can be a list or dictionary.

        Returns:
            None.
        """
        click.secho('\n' + message + '\n', fg='blue')
        index = 1
        for item_id in item_ids:
            try:
                item = self.hacker_news_api.get_item(item_id)
                if item.title:
                    formatted_item = self.format_item(item, index)
                    click.echo(formatted_item)
                    index += 1
            except InvalidItemID:
                self.print_item_not_found(item_id)
        self.save_item_ids()
        click.secho(self.tip_view(str(index-1)))

    def tip_view(self, max_index):
        """Creates the tip about the view command.

        Args:
            * max_index: A string that represents the index upper bound.

        Returns:
            A string representation of the formatted tip.
        """
        tip = click.style(self.TIP0, fg='blue')
        tip += click.style('1 through ', fg='magenta')
        tip += click.style(str(max_index), fg='magenta')
        tip += click.style(self.TIP1, fg='blue')
        tip += click.style(self.TIP2 + '\n', fg='blue')
        return tip

    def url_contents(self, url):
        """Gets the formatted contents of the given item's url.

        Converts the HTML to text using HTML2Text, colors it, then displays
            the output in a pager.

        Args:
            * url: A string representing the url.

        Returns:
            A string representation of the formatted url contents.
        """
        raw_response = requests.get(url)
        contents = self.html_to_text.handle(raw_response.text)
        contents = self.format_markdown(contents)
        contents = click.style(
            'Viewing ' + url + '\n\n', fg='magenta') + contents
        return contents

    def regex_match(self, item, regex_query):
        """Determines if there is a match with the given regex_query.

        Args:
            * item: An instance of haxor.Item.
            * regex_query: A string that specifies the regex query to match.

        Returns:
            A boolean that specifies whether there is a match.
        """
        match_time = re.search(
            regex_query,
            str(pretty_date_time(item.submission_time)))
        match_user = re.search(regex_query, item.by)
        match_text = re.search(regex_query, item.text)
        if not match_text and not match_user and not match_time:
            return False
        else:
            return True

    def save_item_ids(self):
        """Saves the current set of item ids to ~/.hncliconfig.

        Args:
            * None

        Returns:
            None.
        """
        config = self._config(self.CONFIG)
        parser = configparser.RawConfigParser()
        parser.add_section(self.CONFIG_SECTION)
        parser.set(self.CONFIG_SECTION, self.CONFIG_INDEX, self.item_ids)
        parser.write(open(config, 'w+'))

    def show(self, limit):
        """Displays Show HN posts.

        Args:
            * limit: A int that specifies the number of items to show.
                Optional, defaults to 10.

        Returns:
            None.
        """
        self.print_items(
            message=self.headlines_message(self.MSG_SHOW),
            item_ids=self.hacker_news_api.show_stories(limit))

    def top(self, limit):
        """Displays the top posts.

        Args:
            * limit: A int that specifies the number of items to show.
                Optional, defaults to 10.

        Returns:
            None.
        """
        self.print_items(
            message=self.headlines_message(self.MSG_TOP),
            item_ids=self.hacker_news_api.top_stories(limit))

    def user(self, user_id, submission_limit):
        """Displays basic user info and submitted posts.

        Args:
            * user_id: A string representing the user id.
            * submission_limit: A int that specifies the number of
                submissions to show.
                Optional, defaults to 10.

        Returns:
            None.
        """
        try:
            user = self.hacker_news_api.get_user(user_id)
            click.secho('\nUser Id: ', nl=False, fg='magenta')
            click.secho(user_id, fg='yellow')
            click.secho('Created: ', nl=False, fg='magenta')
            click.secho(str(user.created), fg='yellow')
            click.secho('Karma: ', nl=False, fg='magenta')
            click.secho(str(user.karma), fg='yellow')
            self.print_items(self.MSG_SUBMISSIONS,
                             user.submitted[0:submission_limit])
        except InvalidUserID:
            self.print_item_not_found(user_id)

    def load_item_ids(self):
        """Loads item ids from ~/.hncliconfig.

        Args:
            * None.

        Returns:
            A list of ints representing item ids.
        """
        config = self._config(self.CONFIG)
        parser = configparser.RawConfigParser()
        try:
            parser.readfp(open(config))
            items_ids = parser.get(self.CONFIG_SECTION, self.CONFIG_INDEX)
            items_ids = items_ids.strip()
            excludes = ['[', ']', "'"]
            for exclude in excludes:
                items_ids = items_ids.replace(exclude, '')
            return items_ids.split(', ')
        except Exception as e:
            click.secho('Error: ' + str(e), fg='red')
            return None

    def view(self, index, comments_query, comments, browser):
        """Views the given index in a browser.

        Uses ids from ~/.hncliconfig stored in self.item_ids.
        If url is True, opens a browser with the url based on the given index.
        Else, displays the post's comments.

        Args:
            * index: An int that specifies the index to open in a browser.
            * comments_query: A string that specifies the regex query to match.
            * comments: A boolean that determines whether to view the comments
                or a simplified version of the post url.
            * browser: A boolean that determines whether to view the url
                 in a browser.

        Returns:
            None.
        """
        self.item_ids = self.load_item_ids()
        try:
            item = self.hacker_news_api.get_item(self.item_ids[index-1])
        except InvalidItemID:
            self.print_item_not_found(self.item_ids[index-1])
            return
        if not comments and item.url is None:
            click.secho('\nNo url associated with post.',
                        nl=False,
                        fg='blue')
            comments = True
        if comments:
            comments_url = self.URL_POST + str(item.item_id)
            click.secho('\nFetching Comments from ' + comments_url,
                        fg='blue')
            if browser:
                webbrowser.open(comments_url)
            else:
                self.print_comments(item, regex_query=comments_query)
            click.echo('')
        else:
            click.secho('\nOpening ' + item.url + '...', fg='blue')
            if browser:
                webbrowser.open(item.url)
            else:
                contents = self.url_contents(item.url)
                click.echo_via_pager(contents)
            click.echo('')

    def view_setup(self, index, comments_query,
                   comments, comments_recent, browser):
        """Sets up the call to views the given index comments or url.

        This method is meant to be called after a command that outputs a
        table of posts.

        Args:
            * index: A int that specifies the index of a post just shown within
                a table.  For example, calling hn top will list the latest posts
                with indices for each row.  Calling hn view [index] will view
                the comments of the given post.
            * comments_query: A string that specifies the regex query to match.
                This automatically sets comments to True.
            * comments: A boolean that determines whether to view the comments
                or a simplified version of the post url.
            * comments_recent: A boolean that determines whether to view only
                 recently comments (posted within the past 59 minutes or less)
            * browser: A boolean that determines whether to view the url
                 in a browser.

        Returns:
            None.
        """
        if comments_query:
            comments = True
        if comments_recent:
            comments_query = self.QUERY_RECENT
            comments = True
        self.view(int(index),
                  comments_query,
                  comments,
                  browser)
