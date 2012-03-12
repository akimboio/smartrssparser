"""
A Smart Wrapper for the Universal Feed Parser

Smart RSS Parser is a collection of fascades and helper code that wraps around
the Universal Feed Parser library. It helps to normalize data into common
objects regardless of the underlying RSS/atom format

The Universal Feed Parser can be found at:
U{http://code.google.com/p/feedparser}


:author: Adam Haney
:organization Retickr
:contact: adam.haney@retickr.com
:license: Copyright (c) 2011 retickr, LLC
"""

__author__ = "Adam Haney <adam.haney@retickr.com>"
__license__ = "Copyright (c) 2011 retickr, LLC"
__version__ = "0.2.1"

# Import Retickr's special blend of feedparser
import feedparser
import time
import calendar
import warnings
import copy
import pprint
import urllib
import urllib2
import socket
import httplib
import random


class SmartFeedParserDict:
    __name__ = "SmartFeedParserDict"
    """
    This object is a fascade to the feedparser library's FeedParserDict it
    provides a common interface to elements that may appear in different places
    depending upon the protocol of the feed we're crawling
    """

    def create_item(self, name, func, *args, **kwargs):
        """
        This function allows users to create a user defined function to be
        called when an particular named key is accessed. This can extend
        functionality by filling in missing data or it can filter or completely
        override existing data.

        In this case the object does not have a key named 'foo'
        #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> result = smart_parse('http://reddit.com/.rss')
        >>> result["foobar"]
        Traceback (most recent call last):
        KeyError: 'foobar'

        But we can add a method the object (this is called 'Monkey Patching'
        or 'Duck Punching') U{http://en.wikipedia.org/wiki/Monkey_patch}. To do
        this we simply call create_item on the object and pass it a string
        we want to represent the key of the new call. Then we pass it a
        lambda function that takes exactly 1 argument.

        >>> result = smart_parse('http://reddit.com/.rss')
        >>> result.create_item('foo', lambda self_: "some element of any type")
        >>> result['foo']
        'some element of any type'

        If an element of that type already exists in the object's dictionary
        then that value will be passed to the function you have delegated for
        this key.

        >>> result = smart_parse('http://reddit.com/.rss')
        >>> result.create_item('foo', lambda v_: "some element of any type")
        >>> result.create_item('foo', lambda v_: "cooler than, " + v_['foo'])
        >>> result['foo']
        'cooler than, some element of any type'

        @param name: The name of the element that we want to be associated with
            a function This function can be a filter or a complete replacement
            for this value
        @param func: The filter / replacement function for this key
        """
        self_ = copy.deepcopy(self)

        def closure():
            return func(self_, *args, **kwargs)

        return setattr(self, self.__special_extended_item_method_name(name),
                       closure)

    def get(self, name, default):
        """
        This is a convenience wrapper around the object's regular dict_[key_]
        syntax. If the key is not found you may specify a default value to be
        returned. This can allow you to write MUCH more concise code.

        Consider the following examples:

        >>> dict_ = {'a': 'A', 'b': 'B'} #doctest: +IGNORE_EXCEPTION_DETAIL
        >>> dict_['c']
        Traceback (most recent call last):
        KeyError: 'c'

        Normally in order to handle this case we would have to wrap our code
        in exception statements, which can be quite cumbersome. This function
        behaves identically to the following example

        >>> dict_ = {'a': 'A', 'b': 'B'}
        >>> try:
        ...     dict_["c"]
        ... except KeyError:
        ...     "a default value"
        'a default value'

        Instead of this we can instead pass a default value to the get method.
        >>> dict_ = {'a': 'A', 'b': 'B'}
        >>> dict_.get('c', "a default value")
        'a default value'
        """
        try:
            return self.__getitem__(name)
        except KeyError:
            return default

    def update(self, update_dict):
        """
        Allows our SmartFeedDict to behave like Python's built in
        dictionary().update() method.

        We can use update to load a dictionary into the object
        >>> obj_ = SmartFeedParserDict()
        >>> obj_.update({'a': 'A', 'b': 'B'})
        >>> str(obj_)
        "{'a': 'A', 'b': 'B'}"

        We can also use it to over write existing values to fix them
        >>> obj_ = SmartFeedParserDict()
        >>> obj_['a'] = 'B'
        >>> obj_['b'] = 'A'
        >>> obj_['c'] = 'C'
        >>> obj_.update({'a': 'A', 'b': 'B'})

        @param update_dict: a dictionary with values you want to update or add
        """
        for elm in update_dict.keys():
            self.safe_delete(elm)

        self.__feed_dict__.update(update_dict)

    def iteritems(self):
        """
        Currently calls to iteritems only return the original object's
        iteritems in the future this should be extended to return custom
        definted elements
        """
        return self.__feed_dict__.iteritems()

    def pprint(self):
        """
        a convenience function for printing large dictionaries to the screen
        during debugging

        >>> SmartFeedParserDict({'a': 'A', 'b': 'B'}).pprint() #doctest: +SKIP

        """
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(self.__feed_dict__)

    def safe_delete(self, name):
        """
        A convenience wrapper around __delitem__ this call catches
        KeyError exceptions

        We can delete existing elements just like del k[v]
        >>> a = SmartFeedParserDict({'b': 'B', 'c': 'D'})
        >>> a.safe_delete('b')

        But we can also delete elements that aren't contained in the object
        without throwing an exception

        >>> a.safe_delete('f')

        """
        try:
            del self[name]
        except KeyError:
            pass

    @staticmethod
    def escape(str_):
        """
        This is our default general escape function. The first use of this
        object requires that every element we return be utf-8 encoded
        if in the future unicode is desired then this function can be
        replaced by subclassing the object or by patching the object
        at runtime

        >>> SmartFeedParserDict.escape(u'string')
        'string'
        """
        if isinstance(str_, unicode):
            return str_.encode('utf-8', errors='replace')
        return str_

    def __init__(self, feedparserdict=None,
                 update_time_format="%Y-%m-%dT%H:%M:%SZ",
                 encoding_func=None, fuzz_update_time=1):
        """
        Takes a feedparserdict as an argument and returns an instance of
        SmartFeedParserDict.

        >>> SmartFeedParserDict() #doctest: +ELLIPSIS
        {}

        >>> url = 'http://static.retickr.com/testing/rss/reddit.rss'
        >>> type(SmartFeedParserDict(feedparser.parse(url))) #doctest: +ELLIPSIS
        <type 'instance'>

        @param feedparserdict: a feedparserdict object
        @param update_time_format: (optional) a time format to be evaluated by
            time.strftime() which will determine the ouput format when calling
            story["update_time"]
        @param encoding_func: An encoding function to filter returned strings
        @type feedparserdict: FeedParserDict
        """

        if None == feedparserdict:
            self.__feed_dict__ = {}
        elif type(feedparserdict) == list:
            raise TypeError("SmartFeedParserDict cannot represent"\
                                "a list element")
        else:
            self.__feed_dict__ = feedparserdict

        self.update_time_format = update_time_format

        if fuzz_update_time < 1 or type(fuzz_update_time) != int:
            raise ValueError("fuzz update time must"\
                                 "be an integer greater than 1")
        self.fuzz_update_time = fuzz_update_time

    def _get_link(self):
        """
        In an *intelligent* way get the link for the story
        """
        for link in self.get("links", []):
            if "type" in link and link["type"] == "text/html" and "href" in link:
                return link["href"]

        # If we fail to find one of the proper type try to return ANYTHING that has an href
        for link in self.get("links", []):
            if "href" in link:
                return link["href"]

        # If that fails, print self and dump nothing
        return ""

    def _get_source_unescaped_html(self):
        """
        For a given element having the attribute 'link' this method returns
        the resource at that given location as a string

        >>> result = smart_parse('http://reddit.com/.rss')
        >>> html = result["stories"][0].get("source_unescaped_html", "")

        """
        url = smart_url_protocol_guesser(self["link"])
        try:
            return urllib.urlopen(urllib2.Request(url))

        # We assume that an attribute error is a network issue,
        # but because this library is supposed to be helping people who
        # are writing very simple parsers, we return a KeyError in this
        # case that way the get(key) function can catch the Error and
        # return a default value
        except AttributeError:
            raise KeyError

    def _get_story_content(self):
        """
        Overloading the method for getting story content
        """
        longest_elm = reduce(return_longest_element,
                             [self.get('content', ''),
                             self.get('description', ''),
                             self.get('summary', '')])

        if type(longest_elm) == type(list()):
            return longest_elm[0]["value"]

        return longest_elm

    def _get_update_time(self):
        """
        RSS and Atom feeds are sneaky when it comes to update times.
        Sometimes the update time is missing or in some pathelogical cases the
        update time is set to some time in the future. This call takes care
        of those issues. If the update time is missing then we assume that it's
        the gmtime. Also, if the time we find is newer than the current
        gmtime then we return the update time as now.

        >>> # prints the update time of the first story in ISO 8601 format
        >>> result = smart_parse('http://reddit.com/.rss')
        >>> update_time = result["stories"][0]["update_time"]


        By default the time format is "%Y-%m-%d %H:%M%SZ which is the ISO 8601
        time format. This can be changed via the update_time_format parameter
        update_time_format. This attribute will be evaluated by the
        time.strftime function appropriate directives can be found on the
        python website at
        U{http://docs.python.org/library/time.html#time.strftime}

        >>> result = smart_parse('http://reddit.com/.rss')
        >>> result.update_time_format = "%Y"
        >>> # Prints the update time of the story as a Year
        >>> update_time = result["stories"][0]["update_time"]

        @class_variable L{update_time_format}: a string to be evaluated by
            time.strftime() that determines the time format of elements
            containing an update_time
        """

        # Has update time already been computed for us?
        if self.__feed_dict__.has_key("update_time"):
            return self.__feed_dict__["update_time"]

        # Attempt to parse the time from the feed
        try:
            update_time = time.strftime(self.update_time_format,
                                        self.__feed_dict__["updated_parsed"])
        except (TypeError, KeyError):
            # If the story doesn't have an update time give it an update time
            # of now minus a random number of seconds up to fuzz_update_time
            # this lets us reasonably guarantee that if
            # we crawl a feed with many missing story times that the times
            # don't clobber one another in a list of story update times
            # by default the fuzz update time is 0
            fuzz = random.randint(-1 * int(self.fuzz_update_time), int(self.fuzz_update_time))
            update_time = time.strftime(self.update_time_format,
                                        time.gmtime(time.time() + fuzz))

        # Make sure that the time isn't more recent than right now to outsmart
        # wouldbe tricksters
        # TODO: right a test to validate this functionality
        try:
            elm_epoch_time = calendar.timegm(
                time.strptime(update_time, self.update_time_format))
        except ValueError, e:
            elm_epoch_time = time.time() + 5

        if int(elm_epoch_time) > int(time.time()):
            update_time = time.strftime(self.update_time_format, time.gmtime())

        # Don't go through all this logic if we ask for the update time again
        # The update time shouldn't be changing from one call to another
        self.update_time = update_time

        return update_time

    def __len__(self):
        return len(self.__dict__)

    def _get_stories(self):
        """
        A normalized element that is not present in the feedparser dictionary
        by default. This element is the longest (best guess for actual content)
        of the tags: items, content and entries. The goal of this method is to
        provide a common alias for the most useful of any of these tags.

        >>> result = smart_parse('http://reddit.com/.rss')
        >>> type(result["stories"])
        <type 'list'>

        >>> stories = smart_parse('http://reddit.com/.rss')["stories"]
        >>> type(stories[0])
        <type 'instance'>
        """

        raw_stories = return_longest_list_element(
            [self.get("items", []), 
             self.get("entries", []), 
             self.get("content", [])])

        return [make_smart_object(raw_story) for raw_story in raw_stories]

    def __contains__(self, key):
        """
        Tests object for containment of a key.

        >>> x = SmartFeedParserDict()
        >>> x['foo'] = 'bar'
        >>> 'foo' in x
        True

        >>> x = SmartFeedParserDict()
        >>> x['foo'] = 'bar'
        >>> 'bar' in x
        False

        >>> x = SmartFeedParserDict()
        >>> 'bar' in x
        False

        @returns: a boolean indicating if an element is contained in this
            object
        """
        try:
            self.__getitem__(key)
        except KeyError:
            return False

        return True

    has_key = __contains__

    def __repr__(self):
        """
        returns a short representation of the object's location

        >>> type(smart_parse('http://reddit.com/.rss')) #doctest: +ELLIPSIS
        <type 'instance'>
        """
        """
        return '<%s.%s object at %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self)))
        """
        return str(self.__feed_dict__)

    def __str__(self):
        """
        return the string represeentation of the object

        >>> type(str(smart_parse('http://reddit.com/.rss')))
        <type 'str'>

        """
        return str(self.__feed_dict__)

    def __getitem__(self, name):
        """
        We've overridden the getitem method to allow for just in time
        normalization of certain attributes. For example feedparser
        provides

        >>> result = feedparser.parse('http://reddit.com/.rss')
        >>> type(result)
        <class 'feedparser.FeedParserDict'>

        >>> result = feedparser.parse('http://reddit.com/.rss')

        But the problem with this is that the FeedParserDict may contain
        commonly desirable data in different locations. For example,
        result['contents'], result['entries'] and result['description']
        have all been observed to return the "stories" for a feed
        so instead we provide the __get_stories method in this class
        which can be called by accessing result["stories"]

        The encoding function can be overridden to offer more control
        over character encoding and escaping, below is a dummy
        example.

        >>> result = smart_parse('http://reddit.com/.rss')
        >>> result.encoding_func = lambda elm: elm
        >>> stories = result["stories"]


        @class_variable L{encoding_func}: a function to escape strings with
        """

        special_method_name = self.__special_extended_item_method_name(name)

        if hasattr(self, special_method_name):
            attr = getattr(self, special_method_name)
            if callable(attr):
                result = attr()
            else:
                raise AttributeError("%s is defined to be a non callable method" % special_method_name)
        else:
            if name in self.__feed_dict__:
                result = self.__feed_dict__[name]
            else:
                raise KeyError(name)

        return SmartFeedParserDict.escape(result)

    def __delitem__(self, name):
        """
        Because we support the creation, updating, sorting and insertion of key
        value pairs into this object is stands to reason that we sould also
        have support for deleting an element too

        >>> a = {'b': 'B', 'c': 'C'}
        >>> del a['b']

        >>> del a['d'] # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        KeyError: 'd'

        @param name: the name of the element you wish to delete
        """

        if hasattr(self, self.__special_extended_item_method_name(name)):
            delattr(self, self.__special_extended_item_method_name(name))

        elif name in self.__feed_dict__:
            del self.__feed_dict__[name]

        else:
            raise KeyError(name)

    def __special_extended_item_method_name(self, name):
        return "_get_%s" % name

    def __setitem__(self, name, value):
        """
        This method is almost entirely for testing. You shouldn't need to add a
        static value to an object of this type. It's instantiated with values
        so you shouldn't need to set anything. If you would like to extend /
        filter / combine other elements to create a new dictionary take a look
        at the L{create_item} method


        This is an example of the sort of static value you can set
        using set item:

        >>> dict_ = smart_parse('http://reddit.com/.rss')
        >>> dict_['foo'] = 'bar'
        >>> dict_['foo']
        'bar'

        If you would like to create a new dynamic element use the
        create_item method:

        >>> dict_ = smart_parse('http://reddit.com/.rss')
        >>> dict_['foo'] = 'bar'
        >>> foo_function = lambda k: k['foo'].replace('bar', 'cool foo')
        >>> dict_.create_item('foo', foo_function)
        >>> dict_['foo']
        'cool foo'


        @param name: The name of the static element you would like to add to
            the object
        """

        self.__feed_dict__[name] = value


def make_smart_object(obj_, *args, **kwargs):
    """
    This method makes sure that when we receive a nested object such as a
    dictionary of dictionaries or a list of dictionaries that all of those
    dictionaries are converted into smart dictionaries (because we're
    super helpful like that). This allows us to guarantee a common
    __getitem__ interface which simplifies encoding and allows the
    end developer to make some simplier assumptions about the data

    Here we have an element which contains values that are lists and
    dictionaries:

    >>> elm = {'a':{'1', '2'}, 'b': [{'c': 'C'}]}

    the __smart_dictionary_ize method is called by the constructor,
    it shouldn't be called outside of the class

    >>> smrt = make_smart_object(elm)

    The 'a' element contained a set it should now contain a
    set because it isn't iterable

    >>> type(smrt['a'])
    <type 'set'>

    The 'b' element contained a list of dictionary elements it should
    now contain a list os SmartFeedParserDict elements

    >>> type(smrt['b'][0])
    <type 'instance'>
    """

    if type(obj_) == type(SmartFeedParserDict()):
        return obj_

    # This element is a dictionary like item
    elif hasattr(obj_, 'keys'):
        new_obj = SmartFeedParserDict()
        for key in obj_.keys():
            new_obj[key] = make_smart_object(obj_[key])

    # This element is a list, loop through all its elements
    elif type(obj_) == type(list()):
        for ii in range(len(obj_)):
            obj_[ii] = make_smart_object(obj_[ii])
        new_obj = obj_

    # It's something we don't understand, escape then return it
    else:
        new_obj = SmartFeedParserDict.escape(obj_, *args, **kwargs)

    return new_obj


def return_longest_list_element(list_):
    """
    Takes a list as an argument and returns the longest element in that list.

    >>> li = ["adam", "bob", "david"]
    >>> return_longest_list_element(li)
    'david'

    In the case where the list contains elements which have the same length
    then the element appearing earliest in the list has prescedence

    >>> li = ["adam", "bob", "peter", "david"]
    >>> return_longest_list_element(li)
    'peter'

    @param list: a list of elements which have a len attribute
    """

    # Let's just assume for the sake of argument that most humans are idiots
    if type(list_) != type(list()):
        raise TypeError("received a list that wasn't of type <list>")

    longest_index = 0
    longest_element = 0
    for ii in range(len(list_)):
        if len(list_[ii]) > longest_element:
            longest_index = ii
            longest_element = len(list_[ii])

    return list_[longest_index]


def return_longest_element(elm1, elm2, complain=True):
    """
    Takes two objects which have the __len__ attribute, and returns the longest
    of the two, if the len attribute is not present for on of the elements it
    returns the element which does have a __len__ attribute. If neither of the elements
    have a __len__ attribute it raises a TypeError, this can be turned off when calling
    the function by setting the complain parameter to False. In the case where both
    elements are the same length the first element is returned

    @param elm1: an element to be compared which has a len attribute
    @param elm2: an element to be compared which has a len attribute
    @param complain: (optional) a parameter to determine the behavior of the
        function when neither elements has a len attribute, if this is set as
        True and is of type bool(), otherwise when the function would
        normally raise a Type Error it will instead return the value
        of this parameter

        >>> return_longest_element([1, 2, 3], [1, 2])
        [1, 2, 3]

        >>> return_longest_element([1, 7], [1, 4, 7])
        [1, 4, 7]

        >>> return_longest_element([1, 7], 42)
        [1, 7]

        >>> return_longest_element(42, [1, 3])
        [1, 3]

        >>> return_longest_element(42, 43) #doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        TypeError: neither elm1 or elm2 have len() properties

        >>> return_longest_element(42, 43, True) #doctest +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        TypeError: neither elm1 or elm2 have len() properties

        >>> return_longest_element(42, 43, complain=False)
        False

        >>> return_longest_element(42, 43, complain="")
        ''

        >>> return_longest_element([1, 2, 3], [4, 5, 6])
        [1, 2, 3]
        """
    elm1_bozo = False
    try:
        elm1_len = len(elm1)

    except TypeError:
        elm1_bozo = True

    elm2_bozo = False
    try:
        elm2_len = len(elm2)

    except TypeError:
        elm2_bozo = True

    if elm1_bozo and elm2_bozo:
        if complain == True:
            raise TypeError("neither elm1 or elm2 have len() properties")
        else:
            return complain

    elif elm1_bozo:
        return elm2

    elif elm2_bozo:
        return elm1

    elif elm1_len > elm2_len:
        return elm1

    elif elm1_len < elm2_len:
        return elm2

    else:
        return elm1


def smart_url_protocol_guesser(url):
    """
    This function takes a url as an argument that may not be standard compliant,
    it then tries to guess a url path that will work well for crawling the url
    that the user MEANT, obviously guessing isn't optimal but we're going to try
    @param url: a string representing the unsanitized or non standard compliant url
    @type url: string
    @return: url a string representing a url with a proper protocol that has been escaped

    >>> smart_url_protocol_guesser('http://reddit.com/.rss#top')
    'http://reddit.com/.rss%23top'

    >>> smart_url_protocol_guesser('feed://reddit.com/.rss')
    'http://reddit.com/.rss'

    >>> smart_url_protocol_guesser('reddit.com/.rss')
    'http://reddit.com/.rss'

    >>> smart_url_protocol_guesser('http://reddit.com/.rss')
    'http://reddit.com/.rss'

    """

    url = url.strip()

    # Hashes are often contained in urls, and they mess up the ability for us to fetch the
    # resource that we want so we escape them
    url = url.replace("#", "%23")

    # Google chrome lists RSS feeds as 'feed://' because of this let's try to replace
    # 'feed://' with 'http://' to make crawling better
    url = url.replace("feed://", "http://")

    # If the feed doesn't contain a protocol type let's guess that it's http
    if url[:7] != "http://" and url[:8] != "https://":
        url = "http://" + url

    return url


def smart_parse(url, etag=None, modified=None, agent=None, referrer=None,
                handlers=[], request_headers={}, response_headers={},
                encoding_func=None):
    """
    This function takes the url and the general arguments accepted by
    feedparser.parse and then sanitizes the url that we accept to try to guess
    the protocol it also takes the returned FeedParserDict and instead returns
    a SmartFeedParserDict which is an inheritted class that attempts to normalize
    data within this dictionary

    @param url: The url of the resource we wish to crawl, attempts to make smart
        guesses about escaping and protocol
    @type url: string
    @return: a SmartFeedParserDict

    >>> type(smart_parse('http://reddit.com/.rss')) #doctest: +ELLIPSIS
    <type 'instance'>
    """

    #
    # This begins the main body of the function
    #

    # Escape/Sanitized/Determine intent of the url
    url = smart_url_protocol_guesser(url)

    # Escape the url to make sure we can encode it
    url = unicode(url).encode("utf-8", errors='replace')

    # Runs the feedparser.parse method and then wraps the result in our new custom fascade
    return make_smart_object(
        feedparser.parse(url, etag=etag, modified=modified, agent=agent,
                         referrer=referrer, handlers=handlers,
                         request_headers=request_headers,
                         response_headers=response_headers), encoding_func=encoding_func)


def smart_new_story_filter(stories_object, identifier, most_recent_identifier=""):
    """
    This function handles the problem of determinig which stories or entries in
    an RSS feed are newer than stories that we already have (in a file, db,
    or some other persisent data store). This function takes the most
    recent element that WE have, and a list of new stories in chronological
    order. It then returns a list of only stories newer than the
    most_recent_identifier. It usually makes sense for this identifier
    to be title as it is reasonably unique. But these elements could be date
    or some other assumed unique identifier of story elements. 

    @param stories_object: a list of elements that are accessible with
        dictionary notation. This list should be in a meaninful order
        usually chronological. Elements should at least usually contain
        the identifier key. The behavior of the function upon encountering
        a missing identifier key can be determined by channging the
        fail_full_list parameter. By default if an identifier is 
        missing in any element the full list of elements will be returned.
    @param identifier: a reasonibly unique identifier for elements in the 
        list. This can be a title, an update_time or any element contained
        in the story
    @param most_recent_identifier: an element that identifies the most
        recent instance of a unique identifier we know of. For example
        if we had a list of elements:
        [{'num': '1'}, {'num': '2'}, {'num': '3'}]
        and our identifier as 'num' then we might pass this function
        '2' and this function would return [{'num': '1'}], which is
        a list of elements we haven not yet encountered.

    >>> stories_object = [{"title": "Apple"}, {"title": "Bannanna"}, {"title": "Grape"}]
    >>> most_recent_identifier = "Bannanna"
    >>> smart_new_story_filter(stories_object, "title", most_recent_identifier)
    [{'title': 'Apple'}]

    >>> smart_new_story_filter(stories_object, "title", "honeydew")
    [{'title': 'Apple'}, {'title': 'Bannanna'}, {'title': 'Grape'}]

    >>> smart_new_story_filter(stories_object, "foo", "Bannanna")
    [{'title': 'Apple'}, {'title': 'Bannanna'}, {'title': 'Grape'}]

    """

    # Build a list of identifiers maintaining the original order
    # If the key is we have chosen for the indentifier is missing for an element
    # Then we use None as a place holder to maintain the correct mapping of this
    # list to the list of elements that was passed in
    all_none = True
    identifier_list = []
    for elm in stories_object:
        if identifier in elm:
            identifier_list.append(elm[identifier])
            all_none = False
        else:
            identifier_list.append(None)

    if all_none:
        warnings.warn("None of the stories_object elements had the key '%s'. The entire list will be returned unfiltered" % identifier)

    # Get the index of the most_recent_identifier from the list of feed elements
    if most_recent_identifier in identifier_list:
        pivot_identifier_index = identifier_list.index(most_recent_identifier)

    # If it isn't in the list then all of the elements must be new
    else:
        pivot_identifier_index = len(identifier_list)

    # Return a list of new elements
    return stories_object[0:pivot_identifier_index]


def smart_get_favicon_url(url):
    """
    This method tries various means to get a favicon (or better an apple-touch-icon)
    from a given source. This function uses Beautiful Soup to parse the url of the
    http resouce to grab the favicon.

    The following url contains an html page which has its favicon element set,
    here we demonstrate that we can parse that result correctly.

    >>> url = 'http://static.retickr.com/testing/html/reddit.html'
    >>> smart_get_favicon_url(url)
    'http://redditstatic.s3.amazonaws.com/favicon.ico'

    Here is an example of a page that we won't be able to reach over network
    so we'll fail over to procedural guesses.

    >>> smart_get_favicon_url('http://example.com')
    'http://example.com/favicon.ico'

    @param url: The url of the html page or rss feed that you want an icon for.
    """
    import BeautifulSoup
    from urlparse import urlparse, urljoin

    # Start with the 'dumbdest' guess of where the favicon is
    parsed_story_url = urlparse(url)
    favicon = parsed_story_url[0] + "://" + parsed_story_url[1] + "/favicon.ico"

    # A list of rels that are known to be icons
    icon_list = ["apple-touch-icon", "shortcut icon", "icon"]

    # Parse the url using Beautiful Soup
    try:
        html = urllib2.urlopen(urllib2.Request(url), timeout=30).read()
        soup = BeautifulSoup.BeautifulSoup(html)
    except ValueError:
        print url
        return ""

    # These are the exceptions typically thrown when we can't fetch the url
    except (urllib2.HTTPError, urllib2.URLError, socket.timeout,
            httplib.IncompleteRead, httplib.BadStatusLine):
        return favicon

    # The unicode error is particularly nasty, because we don't control what
    # this library does, for now we'll just pass back a dumb url, I'd like to
    # find a better way of dealing with this issue
    except UnicodeError:
        return favicon

    # Iterate over all the link tags in the html contents
    for link in soup('link'):
        if link.has_key('rel') and link.has_key('href') and\
                link['rel'] in icon_list:
            favicon = urljoin(url, link['href'].encode("utf-8").strip())

            return favicon

    # We haven't returned, we must not have found it, return the dumb one
    return favicon

# Run this script directly ro run the tests
if __name__ == "__main__":
    import sys
    usage = "usage: {0} <url-to-parse|doctest>"
    if len(sys.argv) < 2:
        print usage
        exit()

    if "doctest" == sys.argv[1]:
        import doctest
        ELLIPSIS = 1
        IGNORE_EXCEPTION_DETAIL = 1
        doctest.testmod()
    else:
        feed = smart_parse(sys.argv[1])
        feed.pprint()
