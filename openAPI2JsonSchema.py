#!/usr/bin/env python

import json
import yaml
import urllib
import os
import sys
import traceback

from jsonref import JsonRef  # type: ignore
import click

schemaFileCache = {}
@click.command()
@click.option(
    "-o",
    "--output",
    default="schemas",
    metavar="PATH",
    help="Directory to store schema files",
)
@click.argument("schema", metavar="SCHEMA_URL")
def default(output, schema):
    if (len(schema) < 2):
        raise Exception(
            "Invalid schema, schema file location len should larger than 1!")

    workDir = os.getcwd()
    fileNameEndPos = schema.rfind('/')
    #schemaName = ""
    if (fileNameEndPos != -1):
        workDir = schema[0:fileNameEndPos]
        # skip /
        schemaName = schema[fileNameEndPos + 1:]

    os.chdir(workDir)
    if not os.path.exists(output):
        os.makedirs(output)
    print("now work dir is : %s, schema file name is : %s" %
          (workDir, schemaName))
    process(output, schemaName)


def process(output, schema, location="components/schemas"):
    """
    Converts a valid OpenAPI specification into a set of JSON Schema files
    """
    print("Downloading schema, schema is : %s" % schema)
    if sys.version_info < (3, 0):
        response = urllib.urlopen(schema)
    else:
        if os.path.isfile(schema):
            schema = "file://" + os.path.realpath(schema)
        req = urllib.request.Request(schema)
        response = urllib.request.urlopen(req)
    print("Parsing schema, schema is : %s" % schema)
    # Note that JSON is valid YAML, so we can use the YAML parser whether
    # the schema is stored in JSON or YAML
    data = yaml.load(response.read(), Loader=yaml.SafeLoader)

    types = []
    print("Generating individual schemas")

    loc = location.split("/")
    components = data
    for place in loc:
        components = components[place]

    for title in components:
        print("now processing component : %s" % title)
        kind = title.split(".")[-1]  # .lower()

        specification = components[title]
        specification["$schema"] = "http://json-schema.org/schema#"
        specification.setdefault("type", "object")

        full_name = kind
        types.append(title)
        try:
            print("Processing %s" % full_name)

            specification = change_dict_values(
                specification,
                str("components/schemas/" + title).split('/'), schema)

            with open("%s/%s.json" % (output, full_name), "w") as schema_file:
                print("Generating %s.json" % full_name)
                schema_file.write(json.dumps(specification, indent=2))
        except Exception as e:
            print("An error occured processing %s: %s" % (kind, e))
            print("back trace is : %s" % traceback.format_exc())


def getSchema(schema, location):
    print("getSchema: Downloading schema, schema is : %s, location is : %s" %
          (schema, location))

    if (schemaFileCache.has_key(schema) == False):
        if sys.version_info < (3, 0):
            response = urllib.urlopen(schema)
        else:
            if os.path.isfile(schema):
                schema = "file://" + os.path.realpath(schema)
            req = urllib.request.Request(schema)
            response = urllib.request.urlopen(req)
        #print("getSchema: Parsing schema, schema is : %s" % schema)
        # Note that JSON is valid YAML, so we can use the YAML parser whether
        # the schema is stored in JSON or YAML
        data = yaml.load(response.read(), Loader=yaml.SafeLoader)
        schemaFileCache[schema] = data



    loc = location
    components = schemaFileCache[schema]
    for place in loc:
        if (components.has_key(place)):
            components = components[place]
        else:
            raise Exception("do not have components : ", place)
    print("getSchema: get component: %s" % json.dumps(components, indent=2))
    return components


def change_dict_values(d, location, schemaFileName):
    new = {}
    try:
        for k in d.keys():
            new_v = {}
            v = d[k]
            if isinstance(v, dict):
                print("for k %s, the value is dict" % k)
                new_v = change_dict_values(v, location, schemaFileName)
            elif isinstance(v, list):
                print("for k %s, the value is list" % k)
                new_v = list()
                for x in v:
                    new_v.append(
                        change_dict_values(x, location, schemaFileName))
            elif isinstance(v, str):
                if k == "$ref":
                    print("find ref data, ref data is %s" %
                          json.dumps(v, indent=2))
                    schName = schemaFileName
                    loc = location
                    if v[0] != '#':
                        spList = v.split('/')
                        print("the schema is not local, schema name is : %s" %
                              spList[0][0:-1])
                        
                        if len(spList) < 2:
                            print(
                                "invalid ref, the split of ref should be larger than two, ref value is : "
                                % spList[0])
                            raise Exception("Invalid ref!")

                        schName = spList[0]
                        schemaLen = len(schName)
                        if (schemaLen > 2):
                            # get the schema name
                            schName = schName[0:-1]
                            print(
                                "change_dict_values:schema file name is : %s" %
                                schName)
                        else:
                            raise Exception("Invalid schName!")
                        print("location is %s" % loc)
                        loc = spList[1:]
                    else:
                        schName = schemaFileName
                        loc = v.split('/')[1:]
                    new_v = getSchema(schName, loc)
                    new_v = change_dict_values(new_v, loc,schName)
                    return new_v
                    #new.append(new_v)
                    #continue
                else:
                    new_v = v
            else:
                new_v = v
            new[k] = new_v
        return new
    except AttributeError:
        return d


if __name__ == "__main__":
    default()
