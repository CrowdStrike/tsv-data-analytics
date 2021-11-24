"""utlity methods to read and write tsv data."""

from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from io import BytesIO
import base64
import gzip
import json
import os
import time
import zipfile

# local imports
from tsv_data_analytics import tsv
from tsv_data_analytics import file_paths_util
from tsv_data_analytics import file_paths_data_reader
from tsv_data_analytics import file_io_wrapper
from tsv_data_analytics import utils

def merge(tsv_list, merge_def_vals = None):
    # remove zero length tsvs
    tsv_list = list(filter(lambda x: len(x.get_header()) > 0, tsv_list))

    # base condition
    if (len(tsv_list) == 0):
        raise Exception("List of tsv is empty")

    # check for valid headers
    header = tsv_list[0].get_header()
    header_fields = header.split("\t")

    # iterate to check mismatch in header
    index = 0
    for t in tsv_list:
        # Use a different method for merging if the header is different
        if (header != t.get_header()):
            header_diffs = get_diffs_in_headers(tsv_list)
            if (len(header_diffs) > 0):
                utils.warn("Mismatch in header at index: {}. Cant merge. Using merge_intersect for common intersection. Some of the differences in header: {}".format(
                    index, str(header_diffs)))
            else:
                utils.warn("Mismatch in order of header fields: {}, {}. Using merge intersect".format(header.split("\t"), t.get_header().split("\t")))
            return merge_intersect(tsv_list, merge_def_vals)
                
        index = index + 1

    # simple condition
    if (len(tsv_list) == 1):
        return tsv_list[0]
    else:
        return tsv_list[0].union(tsv_list[1:])

def split_headers_in_common_and_diff(tsv_list):
    common = {}
    # get the counts for each header field
    for t in tsv_list:
        for h in t.get_header_fields():
            if (h not in common.keys()):
                common[h] = 0
            common[h] = common[h] + 1

    # find the columns which are not present everywhere
    non_common = []
    for k, v in common.items():
        if (v != len(tsv_list)):
            non_common.append(k)

    # return
    return sorted(common.keys()), sorted(non_common)

def get_diffs_in_headers(tsv_list):
    common, non_common = split_headers_in_common_and_diff(tsv_list)
    return non_common

def merge_intersect(tsv_list, merge_def_vals = None):
    # remove zero length tsvs
    tsv_list = list(filter(lambda x: x.num_rows() > 0, tsv_list))

    # base condition
    if (len(tsv_list) == 0):
        raise Exception("List of tsv is empty")

    # get the first header
    header_fields = tsv_list[0].get_header_fields()

    # some debugging
    diff_cols = get_diffs_in_headers(tsv_list)
    same_cols = []
    for h in header_fields:
        if (h not in diff_cols):
            same_cols.append(h)

    # print if number of unique headers are more than 1
    if (len(diff_cols) > 0):
        # debug
        utils.warn("merge_intersect: missing columns: {}".format(str(diff_cols)))

        # check which of the columns among the diff have default values
        if (merge_def_vals != None):
            # create effective map with empty string as default value
            effective_merge_def_vals = {}

            # some validation. the default value columns should exist somewhere
            for h in merge_def_vals.keys():
                # check if all default columns exist 
                if (h not in diff_cols and h not in same_cols):
                    raise Exception("Default value for a column given which does not exist:", h)

            # assign empty string to the columns for which default value was not defined
            for h in diff_cols:
                if (h in merge_def_vals.keys()):
                    utils.warn("merge_intersect: assigning default value for {}: {}".format(h, merge_def_vals[h]))
                    effective_merge_def_vals[h] = merge_def_vals[h]
                else:
                    utils.warn("merge_intersect: assigning empty string as default value to column:", h)
                    effective_merge_def_vals[h] = ""
        
            # get the list of keys in order
            keys_order = []
            for h in header_fields:
                keys_order.append(h)

            # append the missing columns
            for h in diff_cols:
                if (h not in header_fields):
                    keys_order.append(h)

            # create a list of new tsvs
            new_tsvs = []
            for t in tsv_list:
                t1 = t
                for d in diff_cols:
                    t1 = t1.add_const_if_missing(d, effective_merge_def_vals[d])
                new_tsvs.append(t1.select(keys_order))

            # return after merging
            return merge(new_tsvs)
        else:
            # create a list of new tsvs
            new_tsvs = []
            for t in tsv_list:
                new_tsvs.append(t.select(same_cols))

            return merge(new_tsvs)
    else:
        # probably landed here because of mismatch in headers position
        tsv_list2 = []
        for t in tsv_list:
            tsv_list2.append(t.select(same_cols))
        return merge(tsv_list2) 

def read(input_file_or_files, sep = None, s3_region = None, aws_profile = None):
    input_files = __get_argument_as_array__(input_file_or_files)
    tsv_list = []
    for input_file in input_files:
        # read file content
        lines = file_paths_util.read_file_content_as_lines(input_file, s3_region, aws_profile)

        # take header and dat
        header = lines[0]
        data = lines[1:]

        # check if a custom separator is defined
        if (sep != None):
            # check for validation
            for line in lines:
                if ("\t" in line):
                    raise Exception("Cant parse non tab separated file as it contains tab character:", input_file)

            # create header and data
            header = header.replace(sep, "\t")
            data = [x.replace(sep, "\t") for x in data]

        tsv_list.append(tsv.TSV(header, data))

    return merge(tsv_list)

def read_with_filter_transform(input_file_or_files, filter_transform_func = None, s3_region = None, aws_profile = None):
    # check if filter_func is defined
    if (filter_transform_func == None):
        return read(input_file_or_files, s3_region = s3_region, aws_profile = aws_profile)

    # resolve input
    input_files = __get_argument_as_array__(input_file_or_files)

    # initialize result
    tsv_list = []

    # common keys
    common_keys = {}

    # iterate over all input files
    for input_file in input_files:
        # read the file
        x = read(input_file)

        # update the common
        for h in x.get_header_fields():
            if (h not in common_keys.keys()):
                common_keys[h] = 0
            common_keys[h] = common_keys[h] + 1

        # gather maps of maps
        result_maps = []
        keys = {}

        # iterate over the records of each map and generate a new one
        for mp in x.export_to_maps():
            mp2 = filter_transform_func(mp)
            if (mp2 != None):
                if (len(mp2) > 0):
                    result_maps.append(mp2)
                for k in mp2.keys():
                    keys[k] = 1

        # check for empty maps
        if (len(keys) > 0):
            # output keys
            keys_sorted = []
            first_file = read(input_files[0])
            for h in first_file.get_header_fields():
                if (h in keys.keys()):
                    keys_sorted.append(h)

            # new header and data
            header2 = "\t".join(keys_sorted)
            data2 = []

            # iterate and generate header and data
            for mp in result_maps:
                fields = []
                for k in keys_sorted:
                    fields.append(mp[k])
                data2.append("\t".join(fields))

            # debugging
            utils.debug("tsvutils: read_with_filter_transform: file read: {}, after filter num_rows: {}".format(input_file, len(data2)))

            # result tsv
            tsv_list.append(tsv.TSV(header2, data2))

    # Do a final check to see if all tsvs are empty
    if (len(tsv_list) > 0):
        # call merge on tsv_list
        return merge(tsv_list)
    else:
        # create an empty data tsv file with common header fields
        header_fields = []
        first_file = read(input_files[0])
        for h in first_file.get_header_fields():
            if (common_keys[h] == len(input_files)):
                header_fields.append(h)

        new_header = "\t".join(header_fields)
        new_data = []

        # return
        return tsv.TSV(new_header, new_data)

def read_by_date_range(path, start_date_str, end_date_str, prefix, s3_region = None, aws_profile = None, granularity = "daily"):
    # read filepaths
    filepaths = file_paths_util.read_filepaths(path, start_date_str, end_date_str, prefix, s3_region, aws_profile, granularity)

    # check for headers validity
    if (file_paths_util.has_same_headers(filepaths, s3_region, aws_profile) == False):
        utils.warn("Mismatch in headers for different days. Choose the right date range: start: {}, end: {}".format(start_date_str, end_date_str))
        return None

    # read individual tsvs
    tsv_list = []
    for filepath in filepaths:
        x = read(filepath)
        tsv_list.append(x)

    # combine all together
    if (len(tsv_list) == 0):
        return None
    elif (len(tsv_list) == 1):
        return tsv_list[0]
    else:
        return tsv_list[0].union(tsv_list[1:])

# this method is needed so that users dont have to interact with file_paths_util
# TODO: move this to scar etl tools as there are specific directory construction logic
def get_file_paths_by_datetime_range(path, start_date_str, end_date_str, prefix, spillover_window = 1, s3_region = None, aws_profile = None):
    utils.print_code_todo_warning("get_file_paths_by_datetime_range: move this to scar etl tools as there are specific directory construction logic")
    return file_paths_util.get_file_paths_by_datetime_range(path,  start_date_str, end_date_str, prefix, spillover_window, s3_region, aws_profile)
    
# TODO: move this to scar etl tools as there are specific directory construction logic
def scan_by_datetime_range(path, start_date_str, end_date_str, prefix, filter_func = None, spillover_window = 1, num_par = 5, timeout_seconds = 600, merge_def_vals = None, s3_region = None, aws_profile = None):
    utils.print_code_todo_warning("scan_by_datetime_range: move this to scar etl tools as there are specific directory construction logic")
    utils.warn("scan_by_datetime_range: this method runs in multithreaded mode which can not be stopped without killing process. Wait for timeout_seconds: {}".format(timeout_seconds))

    # read filepaths by scanning. this involves listing all the files, and then matching the condititions
    filepaths = get_file_paths_by_datetime_range(path,  start_date_str, end_date_str, prefix, spillover_window, s3_region, aws_profile)
    utils.info("scan_by_datetime_range: number of paths to read: {}, num_par: {}, timeout_seconds: {}".format(len(filepaths), num_par, timeout_seconds))

    # do some checks on the headers in the filepaths

    # debug
    utils.debug("tsvutils: scan_by_datetime_range: number of files to read: {}".format(len(filepaths)))

    # read all the files in the filepath applying the filter function
    tsv_list = []
    future_list = []
    wait_time = 5

    # submit the tasks
    with ThreadPoolExecutor(max_workers = num_par) as executor:
        counter = 0
        # run loop to submit tasks
        for filepath in filepaths:
            counter = counter + 1
            utils.debug("Submitted task to read: [{}]: {}".format(counter, filepath))
            future = executor.submit(read_with_filter_transform, filepath, filter_func, s3_region, aws_profile)
            future_list.append(future)

        # check for done status after sleeping for 2 seconds
        total_wait = 0
        while True:
            remaining = 0
            running = 0
            for future in future_list:
                # check how many are done
                if (future.done() == False):
                    remaining = remaining + 1
                if (future.running() == True):
                    running = running + 1

            # if all completed then take the result
            if (remaining == 0):
                for future in future_list:
                    x = future.result()
                    tsv_list.append(x)
                break
            else:
                # do some wait
                utils.debug("Total files to read: {}, remaining: {}, running: {}, waiting for: {} seconds".format(len(future_list), remaining, running, wait_time))

                # sleep and increment total wait time
                time.sleep(wait_time)
                total_wait = total_wait + wait_time
                
                # check if total wait time has exceeded the limit
                if (timeout_seconds != None and total_wait >= timeout_seconds):
                    print("scan_by_datetime_range: timeout of {} seconds reached. Shutting down...".format(timeout_seconds))
                    executor.shutdown()
                    print("scan_by_datetime_range: shutdown complete. Raising exception")

                    # break
                    raise Exception("scan_by_datetime_range: timeout of {} seconds reached. Cancelling. To avoid this either change timeout_seconds or filtering criteria.".format(timeout_seconds))

    # completed the threadpool task
    utils.debug("scan_by_datetime_range: Finished reading the files. Calling merge.")
       
    # combine all together
    tsv_combined = merge(tsv_list, merge_def_vals)
    utils.debug("scan_by_datetime_range: Number of records: {}".format(tsv_combined.num_rows()))
       
    return tsv_combined

def load_from_dir(path, start_date_str, end_date_str, prefix, s3_region = None, aws_profile = None, granularity = "daily"):
    # read filepaths
    filepaths = file_paths_util.read_filepaths(path, start_date_str, end_date_str, prefix, s3_region, aws_profile, granularity)
    return load_from_files(filepaths, s3_region, aws_profile)

def load_from_files(filepaths, s3_region, aws_profile):
    # check for headers validity
    if (file_paths_util.has_same_headers(filepaths, s3_region, aws_profile) == False):
        print("Invalid headers.")
        return None

    # initialize the file reader
    file_reader = file_paths_data_reader.FilePathsDataReader(filepaths, s3_region, aws_profile)

    # get header
    header = file_reader.get_header()
    data = []

    # get data
    while file_reader.has_next():
        # read next record
        line = file_reader.next()
        data.append(line)

    # close
    file_reader.close()

    return tsv.TSV(header, data)

def load_from_array_of_map(map_arr):
    # take a union of all keys
    keys = {}

    # iterate over all maps
    for mp in map_arr:
        for k in mp.keys():
            keys[k] = 1

    # sort the keys alphabetically
    sorted_keys = sorted(list(set(keys.keys())))

    # create header
    header = "\t".join(sorted_keys)
    header_fields = header.split("\t")
    header_map = {}
    for i in range(len(header_fields)):
        h = header_fields[i]
        header_map[h] = i

    data = []
    # create data
    for mp in map_arr:
        fields = []
        for k in header_fields:
            v = ""
            if (k in mp.keys()):
                v = str(mp[k])
     
            fields.append(v)

        line = "\t".join(fields)
        data.append(line)

    # create tsv
    return tsv.TSV(header, data)

def save_to_file(tsvfile, output_file_name, s3_region = None, aws_profile = None):
    if (output_file_name.startswith("s3://") == False):
        file_paths_util.create_local_parent_dir(output_file_name)

    # construct output file
    output_file = file_io_wrapper.FileWriter(output_file_name, s3_region, aws_profile)

    # write the data
    output_file.write(tsvfile.get_header() + "\n")
    for line in tsvfile.get_data():
        output_file.write(line + "\n")

    # close file
    output_file.close()

    # debug
    utils.debug("save_to_file: file saved to: {}".format(output_file_name))

def check_exists(tsvfile, s3_region = None, aws_profile = None):
    return file_paths_util.check_exists(tsvfile, s3_region, aws_profile)

def sort_func(vs):
    vs_sorted = sorted(vs, key=lambda y: str(y["date"].replace("-", "")), reverse=True)
    vs_date = [v["date"] for v in vs_sorted]
    return [vs_date[0], ",".join(vs_date[1:])]

def __read_base_url__(url, query_params = {}, headers = {}, username = None, password = None, timeout_sec = 5):
    # check for query params
    if (len(query_params) > 0):
        params_encoded_str = urlencode(query_params)
        url = "{}?{}".format(url, params_encoded_str)
    
    # create request        
    request = Request(url, headers = headers)

    # check for username, password authorization
    if (username != None and password != None and "Authorization" not in headers.keys()):
        # create the authorization header
        base64str = base64.b64encode("{}:{}".format(username, password).encode("ascii")).decode("ascii")
        request.add_header("Authorization", "Basic {}".format(base64str))

    # call urlopen and get response
    response = urlopen(request, timeout = timeout_sec)
        
    # check for error code
    if (response.status != 200):
        raise exception("HTTP response is not 200 OK. Returning:" + response.msg)

    # return response
    return response

def read_url_json(url, query_params = {}, headers = {}, username = None, password = None, timeout_sec = 5):
    # read response
    response_str = read_url_response(url, query_params, headers, username, password, timeout_sec = timeout_sec)

    # parse json object
    json_obj = json.loads(response_str)
    if (isinstance(json_obj, list)):
        lines = []
        for v in json_obj:
            lines.append(utils.url_encode(json.dumps(v)).replace("\n", " "))
        return tsv.TSV("json_encoded", "\n".join(lines)).validate()
    elif (isinstance(json_obj, dict)):
        return tsv.TSV("json_encoded", [utils.url_encode(response_str).replace("\n", " ")]).validate()
    else:
        raise Exception("Unable to parse the json response:", response_str)

def read_url_response(url, query_params = {}, headers = {}, username = None, password = None, timeout_sec = 30):
    # read response
    response = __read_base_url__(url, query_params, headers, username, password, timeout_sec = timeout_sec)

    # check for content type
    content_type = None
    if ("content-type" in response.headers):
        content_type = response.headers["content-type"].lower()
    elif ("Content-Type" in response.headers):
        content_type = response.headers["Content-Type"].lower()
    else:
        raise Exception("Cant find content type in response headers:", str(response.headers))

    # get response
    response_str = None
    if (content_type.startswith("application/x-gzip-compressed")):
        response_str = str(gzip.decompress(response.read()), "utf-8").rstrip("\n")
    elif (content_type.startswith("application/x-zip-compressed")):
        barr = response.read()
        zfile = zipfile.ZipFile(BytesIO(barr))
        response_str = zfile.open(zfile.infolist()[0]).read().decode().rstrip("\n")
        zfile.close()
    elif (content_type.startswith("text/plain") or content_type.startswith("application/json")):
        response_str = response.read().decode("ascii").rstrip("\n")
    else:
        utils.warn("Content Type not detected: {}. Using plain ascii.".format(content_type))
        response_str = response.read().decode("ascii").rstrip("\n")

    # return
    return response_str
        
# TODO: the compressed file handling should be done separately in a function
def read_url(url, query_params = {}, headers = {}, sep = None, username = None, password = None, timeout_sec = 30):
    # use the file extension as alternate way of detecting type of file
    file_type = None
    if (url.endswith(".csv") or url.endswith(".tsv")):
        file_type = "text"
    elif (url.endswith(".gz")):
        file_type = "gzip"
    elif (url.endswith(".zip")):
        file_type = "zip"

    # detect extension  
    ext_type = None
    if (url.endswith(".csv") or url.endswith(".csv.gz") or url.endswith(".csv.zip")):
        ext_type = "csv"
        utils.warn("CSV file detected. Only simple csv files are supported where comma and tabs are not part of any data.")
    elif (url.endswith(".tsv") or url.endswith(".tsv.gz") or url.endswith(".tsv.zip")): 
        ext_type = "tsv"
    else:
        utils.warn("Unknown file extension. Doing best effort in content type detection")

    # read response
    response_str = read_url_response(url, query_params, headers, username, password, timeout_sec = timeout_sec)

    # split into lines
    lines = response_str.split("\n")
    header = lines[0]
    data = lines[1:]

    # check for separator
    if (sep == None and "\t" not in response_str):
        if ("," in header or ext_type == "csv"):
            sep = ","

    # check for other separators
    if (sep != None and sep != "\t"):
        # do a better version of separator detection
        if ("\t" in response_str):
            utils.warn("Non TSV input file has tabs. Converting tabs to spaces")
            header = header.replace("\t", " ")
            data = [x.replace("\t", " ") for x in data]
 
        # replace separator with tabs
        header = header.replace(sep, "\t")
        data = [x.replace(sep, "\t") for x in data]

    # return
    return tsv.TSV(header, data).validate()

# convert from data frame. TODO: df can have multiple header lines coz of indexes
def read_df(df):
    # get the csv str
    tsv_lines = df.to_csv(sep = "\t").rstrip("\n").split("\n")

    # get header and data
    header = tsv_lines[0]
    data = []
    if (len(tsv_lines) > 1):
        data = tsv_lines[1:]

    # return
    return tsv.TSV(header, data)
    
    
# this method returns the arg_or_args as an array of single string if the input is just a string, or return as original array
# useful for calling method arguments that can take single value or an array of values.
# TBD: Relies on fact that paths are never single letter strings
def __get_argument_as_array__(arg_or_args):
    is_single_letter = True
    for i in range(len(arg_or_args)):
        if (len(arg_or_args[i]) > 1):
            is_single_letter = False
            break

    if (is_single_letter == True):
        return [arg_or_args]
    else:
        return arg_or_args

