"""utility methods to do logging. this is more of convenience and very likely to be replaced with better implementation"""

import urllib
import urllib.parse
import json
from json.decoder import JSONDecodeError
import os
import math
import mmh3
import time
from concurrent.futures import ThreadPoolExecutor

# TODO: these caches dont work in multithreaded env.
MSG_CACHE_MAX_LEN = 10000
INFO_MSG_CACHE = {}
ERROR_MSG_CACHE = {}
WARN_MSG_CACHE = {}
DEBUG_MSG_CACHE = {}
TRACE_MSG_CACHE = {}
EXCEPTION_AFTER_WARNINGS_MSG_CACHE = {}
RATE_LIMIT_AFTER_WARNINGS_MSG_CACHE = {}
NOOP_AFTER_WARNINGS_MSG_CACHE= {}

# some env variables
OMIGO_CRITICAL = "OMIGO_CRITICAL"
OMIGO_ERROR = "OMIGO_ERROR"
OMIGO_WARN = "OMIGO_WARN"
OMIGO_INFO = "OMIGO_INFO"
OMIGO_DEBUG = "OMIGO_DEBUG"
OMIGO_TRACE = "OMIGO_TRACE"
OMIGO_WARN_ONCE_ONLY = "OMIGO_WARN_ONCE_ONLY"
OMIGO_DEBUG_REPORT_PROGRESS_PERC = "OMIGO_DEBUG_REPORT_PROGRESS_PERC"
OMIGO_DEBUG_REPORT_PROGRESS_MIN_THRESH = "OMIGO_DEBUG_REPORT_PROGRESS_MIN_THRESH"
OMIGO_CODE_TODO_WARNING = "OMIGO_CODE_TODO_WARNING"
OMIGO_BIG_TSV_WARN_SIZE_THRESH = "OMIGO_BIG_TSV_WARN_SIZE_THRESH"
OMIGO_RATE_LIMIT_N_WARNINGS = "OMIGO_RATE_LIMIT_N_WARNINGS"
OMIGO_NOOP_N_WARNINGS = "OMIGO_NOOP_N_WARNINGS"

def is_critical():
    return str(os.environ.get(OMIGO_CRITICAL, "1")) == "1"

def is_error():
    return str(os.environ.get(OMIGO_ERROR, "1")) == "1"

def is_warn():
    return str(os.environ.get(OMIGO_WARN, "1")) == "1"

def is_info():
    return str(os.environ.get(OMIGO_INFO, "1")) == "1"

def is_debug():
    return str(os.environ.get(OMIGO_DEBUG, "0")) == "1"

def is_trace():
    return str(os.environ.get(OMIGO_TRACE, "0")) == "1"

def is_warn_once_only():
    return str(os.environ.get(OMIGO_WARN_ONCE_ONLY, "1")) == "1"

def get_report_progress():
    return float(os.environ.get(OMIGO_DEBUG_REPORT_PROGRESS_PERC, "0"))

def get_report_progress_min_thresh():
    return float(os.environ.get(OMIGO_DEBUG_REPORT_PROGRESS_MIN_THRESH, "100000"))

def set_report_progress_perc(perc):
    os.environ[OMIGO_DEBUG_REPORT_PROGRESS_PERC] = str(perc)

def set_report_progress_min_thresh(thresh):
    os.environ[OMIGO_DEBUG_REPORT_PROGRESS_MIN_THRESH] = str(thresh)

def get_big_tsv_warn_size_thresh():
    return float(os.environ.get(OMIGO_BIG_TSV_WARN_SIZE_THRESH, "1000000000"))

def set_big_tsv_warn_size_thresh(thresh):
    os.environ[OMIGO_BIG_TSV_WARN_SIZE_THRESH] = str(thresh)

def trace(msg):
    if (is_trace()):
        print("[TRACE]: {}".format(msg))

def trace_once(msg):
    # check if enabled
    if (is_trace() == False):
        return

    # refer to global variable
    global TRACE_MSG_CACHE
    # check if msg is already displayed
    if (msg not in TRACE_MSG_CACHE.keys()):
        print("[TRACE ONCE ONLY]: " + msg)
        TRACE_MSG_CACHE[msg] = 1

        # check if the cache has become too big
        if (len(TRACE_MSG_CACHE) >= MSG_CACHE_MAX_LEN):
            TRACE_MSG_CACHE = {}

def debug(msg):
    if (is_debug()):
        print("[DEBUG]: {}".format(msg))

def debug_once(msg):
    # check if enabled
    if (is_debug() == False):
        return

    # refer to global variable
    global DEBUG_MSG_CACHE
    # check if msg is already displayed
    if (msg not in DEBUG_MSG_CACHE.keys()):
        print("[DEBUG ONCE ONLY]: " + msg)
        DEBUG_MSG_CACHE[msg] = 1

        # check if the cache has become too big
        if (len(DEBUG_MSG_CACHE) >= MSG_CACHE_MAX_LEN):
            DEBUG_MSG_CACHE = {}

def info(msg):
    if (is_info()):
        print("[INFO]: {}".format(msg))

def info_once(msg):
    # check if enabled
    if (is_info() == False):
        return

    # refer to global variable
    global INFO_MSG_CACHE
    # check if msg is already displayed
    if (msg not in INFO_MSG_CACHE.keys()):
        print("[INFO ONCE ONLY]: " + msg)
        INFO_MSG_CACHE[msg] = 1

        # check if the cache has become too big
        if (len(INFO_MSG_CACHE) >= MSG_CACHE_MAX_LEN):
            INFO_MSG_CACHE = {}

def error(msg):
    if (is_error()):
        print("[ERROR]: {}".format(msg))

def error_once(msg):
    # check if enabled
    if (is_error() == False):
        return

    # check if msg is already displayed
    if (msg not in ERROR_MSG_CACHE.keys()):
         print("[ERROR ONCE ONLY]: {}".format(msg))
         ERROR_MSG_CACHE[msg] = 1

         # clear the cache if it has become too big
         if (len(ERROR_MSG_CACHE) >= MSG_CACHE_MAX_LEN):
             ERROR_MSG_CACHE = {}
    else:
        trace(msg)

def enable_critical_mode():
    os.environ[OMIGO_CRITICAL] = "1"

def enable_error_mode():
    os.environ[OMIGO_ERROR] = "1"

def enable_warn_mode():
    os.environ[OMIGO_WARN] = "1"

def enable_info_mode():
    os.environ[OMIGO_INFO] = "1"

def enable_debug_mode():
    os.environ[OMIGO_DEBUG] = "1"

def enable_trace_mode():
    os.environ[OMIGO_TRACE] = "1"

def disable_critical_mode():
    os.environ[OMIGO_CRITICAL] = "0"

def disable_error_mode():
    os.environ[OMIGO_ERROR] = "0"

def disable_warn_mode():
    os.environ[OMIGO_WARN] = "0"

def disable_info_mode():
    os.environ[OMIGO_INFO] = "0"

def disable_debug_mode():
    os.environ[OMIGO_DEBUG] = "0"

def disable_trace_mode():
    os.environ[OMIGO_TRACE] = "0"

def enable_warn_once_only_mode():
    os.environ[OMIGO_WARN_ONCE_ONLY] = "1"

def disable_warn_once_only_mode():
    os.environ[OMIGO_WARN_ONCE_ONLY] = "0"

def warn(msg):
    if (is_warn() or is_error() or is_critical()):
        print("[WARN]: " + msg)

def warn_once(msg):
    # check if enabled
    if (is_warn_once_only() == False):
        return

    # refer to global variable
    global WARN_MSG_CACHE
    # check if msg is already displayed
    if (msg not in WARN_MSG_CACHE.keys()):
        print("[WARN ONCE ONLY]: " + msg)
        WARN_MSG_CACHE[msg] = 1

        # check if the cache has become too big
        if (len(WARN_MSG_CACHE) >= MSG_CACHE_MAX_LEN):
            WARN_MSG_CACHE = {}

def is_code_todo_warning():
    return str(os.environ.get(OMIGO_CODE_TODO_WARNING, "0")) == "1"

def print_code_todo_warning(msg):
    if (is_code_todo_warning()):
        print("[CODE TODO WARNING]: " + msg)

def url_encode(s):
    if (s is None):
        return ""

    return urllib.parse.quote_plus(s)

# TODO: this replaces TAB character
def url_decode(s):
    if (s is None):
        return ""

    return urllib.parse.unquote_plus(s).replace("\n", " ").replace("\t", " ").replace("\v", " ").replace("\r", " ")

def url_decode_clean(s):
    return url_decode(s).replace("\n", " ").replace("\v", " ").replace("\r", " ").replace("\t", " ")

# move this to utils
def parse_encoded_json(s):
    if (s is None):
        return {}

    if (s == ""):
        return {}

    try:
        decoded = url_decode(s)
        if (decoded == ""):
            return {}

        return json.loads(decoded)
    except JSONDecodeError:
        print("Error in decoding json")
        return {}

def encode_json_obj(json_obj):
    return url_encode(json.dumps(json_obj))

# TODO: make it more robust. The object key doesnt have / prefix or suffix
def split_s3_path(path):
    part1 = path[5:]
    index = part1.index("/")
    bucket_name = part1[0:index]

    # boundary conditions
    if (index < len(part1) - 1):
        object_key = part1[index+1:]
    else:
        object_key = ""

    # remove trailing suffix
    if(object_key.endswith("/")):
        object_key = object_key[0:-1]

    return bucket_name, object_key

def get_counts_map(xs):
    mp = {}
    for x in xs:
        if (x not in mp):
            mp[x] = 0
        mp[x] = mp[x] + 1

    return mp

def report_progress(msg, dmsg, counter, total):
    report_progress = get_report_progress()
    report_progress_min_threshold = get_report_progress_min_thresh()
    msg2 = dmsg + ": " + msg if (dmsg is not None and len(dmsg) > 0) else msg
    if (is_debug() and report_progress > 0 and total >= report_progress_min_threshold):
        progress_size = int(report_progress * total)
        if (progress_size > 0 and counter % progress_size == 0):
            progress_perc = int(math.ceil(100 * counter / total))
            debug("{}: {}% ({} / {})".format(msg2, progress_perc, counter, total))

def merge_arrays(arr_list):
    result = []
    for arr in arr_list:
        for v in arr:
            result.append(v)

    return result

def is_array_of_string_values(col_or_cols):
    if (isinstance(col_or_cols, str)):
        return False

    is_array = False
    for c in col_or_cols:
        if (len(c) > 1):
            is_array = True
            break
    return is_array

def is_numeric(v):
    return str(v).isnumeric()

def is_float(v):
    try:
        float(str(v))
        return True
    except:
        return False

def is_int_col(xtsv, col):
    raise Exception("Deprecated. The to_df() method supports inferring data types")

def is_float_col(xtsv, col):
    raise Exception("Deprecated. The to_df() method supports inferring data types")

def is_pure_float_col(xtsv, col):
    raise Exception("Deprecated. The to_df() method supports inferring data types")

def is_float_with_fraction(xtsv, col):
    raise Exception("Deprecated. The to_df() method supports inferring data types")

def compute_hash(x, seed = 0):
    return abs(mmh3.hash64(str(x) + str(seed))[0])

class ThreadPoolTask:
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

def run_with_thread_pool(tasks, num_par = 4, wait_sec = 10, post_wait_sec = 0, dmsg = ""):
    dmsg = extend_inherit_message(dmsg, "run_with_thread_pool")

    # debug
    if (num_par > 0):
        info("{}: num tasks: {}, num_par: {}".format(dmsg, len(tasks), num_par))

    # define results
    results = []

    # check if this is to be run in multi threaded mode or not
    if (num_par == 0):
        debug("{}: running in single threaded mode".format(dmsg))

        # iterate
        for task in tasks:
            func = task.func
            args = task.args
            kwargs = task.kwargs
            results.append(func(*args, **kwargs))

        # return
        return results
    else:
        # start thread pool
        future_results = []
        with ThreadPoolExecutor(max_workers = num_par) as executor:
            # iterate over tasks and call submit
            for i in range(len(tasks)):
                # call submit
                func = tasks[i].func
                args = tasks[i].args
                kwargs = tasks[i].kwargs
                future_results.append(executor.submit(func, *args, **kwargs))

            # wait for completion
            while True:
                done_count = 0
                for f in future_results:
                    if (f.done() == True):
                        done_count = done_count + 1

                # check if all are done
                if (done_count < len(future_results)):
                    # sleep for some additional time to allow notebook stop method to work
                    info("{}: futures not completed yet. Status: {} / {}. Sleeping for {} sec".format(dmsg, done_count, len(future_results), wait_sec))
                    time.sleep(wait_sec)
                else:
                    info("{}: run_with_thread_pool: finished".format(dmsg))
                    break

            # combine the results
            for f in future_results:
                results.append(f.result())

            # wait for post_wait_sec for mitigating eventual consistency
            if (post_wait_sec > 0):
                info("{}: sleeping for post_wait_sec: {}".format(dmsg, post_wait_sec))
                time.sleep(post_wait_sec)

            # return
            return results

def raise_exception_or_warn(msg, ignore_if_missing, max_len = 2000):
    # strip the message to max_len
    if (max_len is not None and max_len > 0 and len(msg) > max_len):
        msg = msg[0:max_len] + " ..."

    # print message if ignore_if_missing flag is true
    if (ignore_if_missing == True):
        debug_once(msg)
    else:
        raise Exception(msg)

def error_and_raise_exception(msg, max_len = 2000):
    # strip the message to max_len
    if (max_len is not None and max_len > 0 and len(msg) > max_len):
        msg = msg[0:max_len] + " ..."

    # print error
    error(msg)

    # raise exception
    raise Exception(msg)

def raise_exception_after_n_warnings(msg, num_warnings = 1000):
    global EXCEPTION_AFTER_WARNINGS_MSG_CACHE

    # check if msg is new
    if (msg not in EXCEPTION_AFTER_WARNINGS_MSG_CACHE.keys()):
        EXCEPTION_AFTER_WARNINGS_MSG_CACHE[msg] = 1

    # check the counter
    if (EXCEPTION_AFTER_WARNINGS_MSG_CACHE[msg] < num_warnings):
        EXCEPTION_AFTER_WARNINGS_MSG_CACHE[msg] = EXCEPTION_AFTER_WARNINGS_MSG_CACHE[msg] + 1
        warn_once(msg)
    else:
        del EXCEPTION_AFTER_WARNINGS_MSG_CACHE[msg]
        raise Exception(msg)

def rate_limit_after_n_warnings(msg, num_warnings = None, sleep_secs = 10):
    global RATE_LIMIT_AFTER_WARNINGS_MSG_CACHE

    # resolve num_warnings
    num_warnings = int(resolve_default_parameter("num_warnings", os.getenv(OMIGO_RATE_LIMIT_N_WARNINGS), "10000", "rate_limit_after_n_warnings"))

    # check if msg is new
    if (msg not in RATE_LIMIT_AFTER_WARNINGS_MSG_CACHE.keys()):
        RATE_LIMIT_AFTER_WARNINGS_MSG_CACHE[msg] = 1

    # check the counter
    if (num_warnings == -1 or RATE_LIMIT_AFTER_WARNINGS_MSG_CACHE[msg] < num_warnings):
        RATE_LIMIT_AFTER_WARNINGS_MSG_CACHE[msg] = RATE_LIMIT_AFTER_WARNINGS_MSG_CACHE[msg] + 1
        warn_once(msg)
    else:
        trace("{}: Sleeping for {} seconds".format(msg, sleep_secs))
        time.sleep(sleep_secs)

def noop_after_n_warnings(msg, func, *args, **kwargs):
    global NOOP_AFTER_WARNINGS_MSG_CACHE

    # resolve num_warnings
    num_warnings = int(resolve_default_parameter("num_warnings", os.getenv(OMIGO_NOOP_N_WARNINGS), "10000", "noop_after_n_warnings"))

    # check if msg is new
    if (msg not in NOOP_AFTER_WARNINGS_MSG_CACHE.keys()):
        NOOP_AFTER_WARNINGS_MSG_CACHE[msg] = 1

    # check the counter
    if (num_warnings == -1 or NOOP_AFTER_WARNINGS_MSG_CACHE[msg] < num_warnings):
        NOOP_AFTER_WARNINGS_MSG_CACHE[msg] = NOOP_AFTER_WARNINGS_MSG_CACHE[msg] + 1
        func(*args, **kwargs)
        warn_once(msg)
    else:
        trace("{}: noop".format(msg, sleep_secs))

# Deprecated
def strip_spl_white_spaces(v):
    warn_once("Deprecated: Instead of strip_spl_white_spaces use replace_spl_white_spaces_with_space")
    return replace_spl_white_spaces_with_space(v)

def replace_spl_white_spaces_with_space(v):
    # check None
    if (v is None):
        return None

    # return
    return str(v).replace("\t", " ").replace("\n", " ").replace("\v", " ").replace("\r", " ")

def resolve_meta_params(xstr, props):
    # check for None
    if (xstr is None):
        return None

    # iterate through properties
    for k in props.keys():
        kstr = "{" + k + "}"
        xstr = xstr.replace(kstr, str(props[k]))

    # return
    return xstr

def replace_template_props(props, xstr):
    # validation
    if (xstr is None or xstr == ""):
        return xstr

    # iterate
    for k in props.keys():
        # generate template key
        template_key = "{" + k + "}"
        if (xstr.find(template_key) != -1):
            xstr = xstr.replace(template_key, str(props[k]))

    # return
    return xstr

def random_shuffle(xs, seed = 0):
    # boundary conditions
    if (xs is None or len(xs) <= 1):
        return xs

    # apply seed
    index = seed % len(xs)

    # create a copy
    xs2 = list([t for t in xs])

    # swap item 0 with item[seed]
    temp = xs2[0]
    xs2[0] = xs2[index]
    xs2[index] = temp
 
    # return
    return xs2

def is_text_content_col(col, text_columns):
    warn_once("is_text_content_col: this api needs more consistency across the board")

    # validation
    if (col is None):
        return False

    # check for text_columns
    if (text_columns is None or len(text_columns) == 0):
        return False

    # use case insensitive matching
    for tcol in text_columns:
        if (col.lower() == tcol.lower()):
            return True

    return False

def resolve_default_parameter(name, value, default_value, msg):
    # check if prefix parameter is None
    if (value is None):
        default_value_display = str(default_value)
        default_value_display = default_value_display if (len(default_value_display) < 30) else default_value_display[0:30] + "..."
        warn_once("{}: {} value is None. Using default value: {}".format(msg, name, default_value_display))
        value = default_value

    # return
    return value

def extend_inherit_message(old_msg, new_msg):
     # check if both msgs are defined
     if (old_msg is not None and new_msg is not None):
         parts1 = list([t.strip() for t in old_msg.split(":")])
         parts2 = list([t.strip() for t in new_msg.split(":")])

         # do a fuzzy match
         if (len(parts2) == 2):
             if (len(parts1) >= 2 and parts1[-2] == parts2[0]):
                 new_msg = parts2[1]
             elif (len(parts1) >= 3 and parts1[-3] == parts2[0]):
                 new_msg = parts2[1]
             elif (len(parts1) >= 4 and parts1[-4] == parts2[0]):
                 new_msg = parts2[1]
             elif (len(parts1) >= 5 and parts1[-5] == parts2[0]):
                 new_msg = parts2[1]

     # return
     return "{}: {}".format(old_msg, new_msg) if (old_msg is not None and len(old_msg) > 0) else "{}".format(new_msg)

def max_dmsg_str(dmsg, max_len = 300):
    if (dmsg is None or len(dmsg) <= max_len):
        return dmsg
    else:
        return "{}... ".format(dmsg[0:max_len - 4])

def is_tsv_file_extension(path):
    # check extensions
    if (path.endswith(".tsv") or path.endswith(".tsv.gz") or path.endswith(".csv") or path.endswith(".csv.gz")):
        return True
    else:
        return False

# TODO: Move this to proper package 
class CombGenerator:
    def __init__(self):
        self.comb1_cache = {}
        self.comb2_cache = {}
        self.comb3_cache = {}
        self.comb4_cache = {}
        self.comb5_cache = {}
        self.comb6_cache = {}
        self.comb7_cache = {}

    def gen_comb1(self, n):
        if (n not in self.comb1_cache.keys()):
            self.comb1_cache[n] = self.__gen_comb1__(n)
        return self.comb1_cache[n]

    def gen_comb2(self, n):
        if (n not in self.comb2_cache.keys()):
            self.comb2_cache[n] = self.__gen_comb2__(n)
        return self.comb2_cache[n]

    def gen_comb3(self, n):
        if (n not in self.comb3_cache.keys()):
            self.comb3_cache[n] = self.__gen_comb3__(n)
        return self.comb3_cache[n]

    def gen_comb4(self, n):
        if (n not in self.comb4_cache.keys()):
            self.comb4_cache[n] = self.__gen_comb4__(n)
        return self.comb4_cache[n]

    def gen_comb5(self, n):
        if (n not in self.comb5_cache.keys()):
            self.comb5_cache[n] = self.__gen_comb5__(n)
        return self.comb5_cache[n]

    def gen_comb6(self, n):
        if (n not in self.comb6_cache.keys()):
            self.comb6_cache[n] = self.__gen_comb6__(n)
        return self.comb6_cache[n]

    def gen_comb7(self, n):
        if (n not in self.comb7_cache.keys()):
            self.comb7_cache[n] = self.__gen_comb7__(n)
        return self.comb7_cache[n]

    def __gen_comb1__(self, n):
       result = []
       for i1 in range(0, n):
           result.append([i1])
       return result
    
    def __gen_comb2__(self, n):
       result = []
       for i2 in range(0, n-1):
           for i1 in range(i2+1, n):
               result.append([i2, i1])
       return result
    
    def __gen_comb3__(self, n):
       result = []
       for i3 in range(0, n-2):
           for i2 in range(i3+1, n-1):
               for i1 in range(i2+1, n):
                   result.append([i3, i2, i1])
       return result
    
    def __gen_comb4__(self, n):
       result = []
       for i4 in range(0, n-3):
           for i3 in range(i4+1, n-2):
               for i2 in range(i3+1, n-1):
                   for i1 in range(i2+1, n):
                       result.append([i4, i3, i2, i1])
       return result
    
    def __gen_comb5__(self, n):
       result = []
       for i5 in range(0, n-4):
           for i4 in range(i5+1, n-3):
               for i3 in range(i4+1, n-2):
                   for i2 in range(i3+1, n-1):
                       for i1 in range(i2+1, n):
                           result.append([i5, i4, i3, i2, i1])
       return result
    
    def __gen_comb6__(self, n):
       result = []
       for i6 in range(0, n-5):
           for i5 in range(i6+1, n-4):
               for i4 in range(i5+1, n-3):
                   for i3 in range(i4+1, n-2):
                       for i2 in range(i3+1, n-1):
                           for i1 in range(i2+1, n):
                               result.append([i6, i5, i4, i3, i2, i1])
       return result
    
    def __gen_comb7__(self, n):
       result = []
       for i7 in range(0, n-6):
           for i6 in range(i7+1, n-5):
               for i5 in range(i6+1, n-4):
                   for i4 in range(i5+1, n-3):
                       for i3 in range(i4+1, n-2):
                           for i2 in range(i3+1, n-1):
                               for i1 in range(i2+1, n):
                                   result.append([i7, i6, i5, i4, i3, i2, i1])
       return result


def split_str_to_arr(x):
    if (x is None or x == ""):
        return []
    else:
        return list(filter(lambda t: t != "", x.split(",")))

    # get string
    result = " ".join(results)

    # return
    return result

def validate_nonnull_params(*args, **kwargs):
    # iterate and throw exception if any of the parameters is None
    for k in kwargs:
        if (kwargs[k] is None):
            raise Exception("Found None value in a mandatory parameter: {}".format(k))

def convert_ipv4_to_hex(ip):
    # validation
    if (ip is None or ip == ""):
        raise Exception("convert_ipv4_to_hex: invalid input: {}".format(ip))

    # split
    parts = ip.split('.')

    # validation
    if (len(parts) != 4):
        raise Exception("convert_ipv4_to_hex: invalid input: {}".format(ip))

    # convert
    hex_parts = hex(int(parts[0])) + hex(int(parts[1])) + hex(int(parts[2])) + hex(int(parts[3]))

    # return
    return hex_parts.replace('0x', '')

def logger_info(logger, msg):
    if (is_info()):
        logger.info(msg)

def logger_warn(logger, msg):
    if (is_warn()):
        logger.warn(msg)

# this method returns the arg_or_args as an array of single string if the input is just a string, or return as original array
# useful for calling method arguments that can take single value or an array of values.
# TBD: Relies on fact that paths are never single letter strings
def get_argument_as_array(arg_or_args):
    # check if it is of type list
    if (isinstance(arg_or_args, list)):
        if (len(arg_or_args) == 0):
            raise Exception("get_argument_as_array: empty list")
        elif (len(arg_or_args) == 1):
            return get_argument_as_array(arg_or_args[0])

    # check for single letter string
    is_single_letter = True
    for i in range(len(arg_or_args)):
        if (len(arg_or_args[i]) > 1):
            is_single_letter = False
            break

    if (is_single_letter == True):
        return [arg_or_args]
    else:
        return arg_or_args

def is_url_encoded_col(col):
    if (col is not None and col.endswith(":url_encoded")):
        return True
    else:
        return False
