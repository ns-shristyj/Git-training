import os, json, fileinput, reportlab, pathlib, yaml, sqlite3, platform, uuid, hashlib, time
from flask import Flask, request, jsonify
from spdx_tools.spdx.parser.parse_anything import parse_file
from spdx_tools.spdx.writer.write_anything import write_file
from spdx_tools.spdx.validation.document_validator import validate_full_spdx_document
from spdx_tools.spdx.model.document import Document
from spdx_tools.spdx.parser.error import SPDXParsingError
import sqlalchemy
from sqlalchemy import text
from models import db, User, Vendor, Component, Vulnerability

app = Flask(__name__)


def fetchConfig():
    check = {}
    try:
        with open(os.path.abspath(os.environ['EMU_INSTALL_PATH'] + '\\config.YAML'), 'r') as stream:
            yaml_stream = stream.read()
        config = yaml.safe_load(os.path.expandvars(yaml_stream))
        check['status'] = "Success"
        check['message'] = "Config loaded successfully..."
        check['config'] = config
        return (check)
    except Exception as e:
        check['status'] = "Error"
        check['message'] = f"{e}"
        return (check)


def setInstallPath():
    os.environ['EMU_INSTALL_PATH'] = str(os.path.abspath(".\\"))


def setPlatform():
    ops = platform.system()
    if ops == "Windows":
        os.environ['EMU_PLATFORM'] = "Windows"
    elif ops == "Linux":
        os.environ['EMU_PLATFORM'] = "Linux"
    elif ops == "Darwin":
        os.environ['EMU_PLATFORM'] = "MacOS"
    else:
        os.environ['EMU_PLATFORM'] = "Unknown"


def test_db_connection(dbPath=None):
    check = {}
    attempts = 0
    while attempts != 3:
        try:
            engine = sqlalchemy.create_engine(f"sqlite:///{dbPath}")
            with engine.connect() as connection:
                connection.execute(text("SELECT sqlite_version();"))
                connection.commit()
            check['status'] = "Success"
            check['message'] = "Database connection successful..."
            return(check)
        except Exception as e:
            check['status'] = "Error"
            check['message'] = f"{e}"
            attempts += 1
            if attempts == 3:
                return(check)


def initialize():
    setInstallPath()
    setPlatform()
    if os.environ['EMU_PLATFORM'] == "Unknown":
        print("Unknown OS detected. Please run on a supported OS.")
        exit(1)
    config_check = fetchConfig()
    if config_check['status'] == "Success":
        print(config_check['message'])
        config = config_check['config']
        os.environ['EMU_CONFIG_PATH'] = os.path.abspath(config['CONFIG_PATH'])
        db_check = test_db_connection(dbPath=os.path.abspath(config['DB_PATH']))
        if db_check['status'] == "Success":
            print(db_check['message'])
        elif db_check['status'] == "Error":
            print(db_check['message'])
            exit(1)
    elif config_check['status'] == "Error":
        print(config_check['message'])
        exit(1)


def check_extension(filename, allowedExt):
    extension = filename.split(".")[-1]
    if extension in allowedExt:
        return (True)
    else:
        return (False)


def store_in_localdb(data, id, type, dbpath):
    config = fetchConfig()
    check = {}
    testConnection = test_db_connection(dbpath)
    if testConnection['status'] == "Success":
        if type == "spdx":
            try:
                data = json.load(open(data))
                packages = data['packages']
                # engine = sqlalchemy.create_engine(f"sqlite:///{os.path.abspath(config['DB_PATH'])}")
                for pack in packages:
                    print(pack)
                    new_pack = Component(id=id,name=pack['name'],license=pack['licenseDeclared'],package_url=pack['downloadLocation'])
                    db.session.add(new_pack)
                    db.session.commit()
                check['status'] = "Success"
                check['message'] = 'Upload to database successful'
                return(check)
            except Exception as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return(check)
        elif type == "cydx":
            try:
                data = json.load(open(data))
                components = data['Components']
                # engine = sqlalchemy.create_engine(f"sqlite:///{os.path.abspath(config['DB_PATH'])}")
                for comp in components:
                    print(comp)
                    new_comp = Component(id=id, name=comp['name'])
                    db.session.add(new_comp)
                    db.session.commit()
                check['status'] = "Success"
                check['message'] = 'Upload to database successful'
                return(check)
            except Exception as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return(check)
    elif testConnection['status'] == "Error":
        check['status'] = "Error"
        check['message'] = f"{testConnection['message']}"
        return(check)


def generate_uuid(filename):
    tokenization = {}
    id = str(uuid.uuid1())
    #hash = hashlib.file_digest(file, "SHA256").hexdigest()
    extension = filename.split(".")[-1]
    tokenization['fileId'] = id
    #tokenization['sha256'] = hash
    tokenization['ext'] = extension
    return (tokenization)


def convert_to_json(data, temp, cyclone_path=None, spdx=None, cyclone=None):
    check = {}

    try:
        if spdx:
            try:
                spdxDoc = parse_file(os.path.abspath(data))
                write_file(document=spdxDoc, file_name=os.path.abspath(temp), validate=True)
                check['status'] = "Success"
                check['message'] = "Successfully converted spdx file to json."
                return (check)
            except Exception as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return (check)
        elif cyclone:
            try:
                response = os.popen(
                    f'"{cyclone_path}" convert --input-file "{os.path.abspath(data)}" --input-format autodetect --output-format json --output-file "{os.path.abspath(temp)}"').read()
                print(response)
                check['status'] = "Success"
                check['message'] = "Successfully converted cyclone-dx file to json."
                return (check)
            except Exception as e:
                check['status'] = "Error"
                check['message'] = f"{e}"
                return (check)
    except Exception as e:
        check['status'] = "Error"
        check['message'] = f"{e}"
        return (check)


def cyclone_check(doc, cyclone_path):
    check = {}

    try:
        result = os.popen(f'"{cyclone_path}" validate --fail-on-errors --input-file "{doc}" --input-format autodetect').readlines()
        print(result)

        if result == []:
            check['status'] = "Error"
            check['message'] = f"Invalid file format"
            return (check)
        elif result != []:
            for i in result:
                if "BOM is not valid." in i or "Unable to auto-detect input format" in i:
                    check['status'] = "Error"
                    check['message'] = f"{result}"
                    return (check)
            check['status'] = "Success"
            check['message'] = f"{result}"
            return (check)

    except os.error as e:
        check['status'] = "Error"
        check['message'] = f"{e}"
        return (check)
    except Exception as e:
        check['status'] = "Error"
        check['message'] = f"{e}"
        return (check)


def spdx_check(doc):
    check = {}

    try:
        spdxDoc = parse_file(doc)
        validate = validate_full_spdx_document(spdxDoc)
        print(validate)
        check['status'] = "Success"
        check['message'] = "SPDX format detected"
        return (check)
    except SPDXParsingError as e:
        check['status'] = "Error"
        check['message'] = f"{e}"
        return (check)
    except AttributeError as e:
        check['status'] = "Error"
        check['message'] = f"{e}"
        return (check)
    except Exception as e:
        check['status'] = "Error"
        check['message'] = f"{e}"
        return (check)


def file_output(fileOut, fmt=None):
    for f in fileOut:
        print(f)


def validate_file(fileIn, cyclone_path):
    check = {}

    firstCheck = spdx_check(os.path.abspath(fileIn))
    print(firstCheck)
    if firstCheck['status'] == "Success":
        check['status'] = "Success"
        check['message'] = f"File validated with SPDX-Tools"
        check['method'] = "spdx"
        return (check)
    elif firstCheck['status'] == "Error":
        secondCheck = cyclone_check(os.path.abspath(fileIn), os.path.abspath(cyclone_path))
        print(secondCheck)
        if secondCheck['status'] == "Success":
            check['status'] = "Success"
            check['message'] = f"File validated with CycloneDX"
            check['method'] = "cydx"
            return (check)
        elif secondCheck['status'] == "Error":
            check['status'] = "Error"
            check['message'] = f"Un-supported file type. Please use a supported file type. File:{os.path.abspath(fileIn)}"
            return (check)


@app.route('/upload', methods=["POST"])
def init_web():
    config_check = fetchConfig()
    if config_check['status'] == "Success":
        config = config_check['config']
        tempFolder = f'{os.path.abspath(config['TEMP_PATH'])}'
        dataFolder = f'{os.path.abspath(config['DATA_PATH'])}'
        allowedExt = f'{config['ALLOWED_EXT']}'

        if 'file' not in request.files:
            return (jsonify({"status": 400, "message": "No file found"}))

        file = request.files['file']
        if file.filename == '':
            return (jsonify({"status": 400, "message": "Blank filename"}))

        if file and check_extension(file.filename, allowedExt):
            tokenz = generate_uuid(file.filename)
            dataUpload = os.path.join(dataFolder, tokenz['fileId'] + "." + tokenz['ext'])
            file.save(dataUpload)
            
            if config['PLATFORM'] == "Windows":
                check = validate_file(dataUpload, config['CYDX_WIN_PATH'])
                print(check)
                if check['status'] == "Success":
                    tempUpload = os.path.join(tempFolder, str(tokenz['fileId']) + ".json")
                    if check['method'] == "spdx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, spdx=True)
                        print(check)
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), tokenz['fileId'], "spdx", config['DB_PATH'])
                            if check['status'] == "Success":
                                return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif check['status'] == "Error":
                            os.remove(dataUpload)
                            return (jsonify({"status": 400, "message": f"{check['message']}"}))

                    elif check['method'] == "cydx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, cyclone_path=config['CYDX_WIN_PATH'], cyclone=True)
                        print(check)
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), tokenz['fileId'], "cydx", config['DB_PATH'])
                            if check['status'] == "Success":
                                return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif config_check['status'] == "Error":
                            os.remove(dataUpload)
                            return (jsonify({"status": 400, "message": f"{check['message']}"}))                        
                elif check['status'] == "Error":
                    os.remove(dataUpload)
                    return (jsonify({"status": 400, "message": f"{check['message']}"}))
                
            elif config['PLATFORM'] == "Linux":
                check = validate_file(dataUpload, config['CYDX_LIN_PATH'])
                print(check)
                if check['status'] == "Success":
                    tempUpload = os.path.join(tempFolder, str(tokenz['fileId']) + ".json")
                    if check['method'] == "spdx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, spdx=True)
                        print(check)
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), tokenz['fileId'], "spdx", config['DB_PATH'])
                            if check['status'] == "Success":
                                return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif check['status'] == "Error":
                            os.remove(dataUpload)
                            return (jsonify({"status": 400, "message": f"{check['message']}"}))

                    elif check['method'] == "cydx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, cyclone_path=config['CYDX_LIN_PATH'], cyclone=True)
                        print(check)
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), tokenz['fileId'], "cydx", config['DB_PATH'])
                            if check['status'] == "Success":
                                return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif config_check['status'] == "Error":
                            os.remove(dataUpload)
                            return (jsonify({"status": 400, "message": f"{check['message']}"}))
                elif check['status'] == "Error":
                    os.remove(dataUpload)
                    return (jsonify({"status": 400, "message": f"{check['message']}"}))
                
            elif config['PLATFORM'] == "MacOS":
                check = validate_file(dataUpload, config['CYDX_MAC_PATH'])
                print(check)
                if check['status'] == "Success":
                    tempUpload = os.path.join(tempFolder, str(tokenz['fileId']) + ".json")
                    if check['method'] == "spdx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, spdx=True)
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), tokenz['fileId'], "spdx", config['DB_PATH'])
                            if check['status'] == "Success":
                                return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif check['status'] == "Error":
                            os.remove(dataUpload)
                            return (jsonify({"status": 400, "message": f"{check['message']}"}))

                    elif check['method'] == "cydx":
                        check = convert_to_json(data=dataUpload, temp=tempUpload, cyclone_path=config['CYDX_MAC_PATH'], cyclone=True)
                        print(check)
                        if check['status'] == "Success":
                            check = store_in_localdb(os.path.abspath(tempUpload), tokenz['fileId'], "cydx", config['DB_PATH'])
                            if check['status'] == "Success":
                                return (jsonify({"status": 200, "message": "Upload successful"}))
                            elif check['status'] == "Error":
                                os.remove(dataUpload)
                                os.remove(tempUpload)
                                return (jsonify({"status": 400, "message": f"{check['message']}"}))
                        elif config_check['status'] == "Error":
                            os.remove(dataUpload)
                            return (jsonify({"status": 400, "message": f"{check['message']}"}))
                elif check['status'] == "Error":
                    os.remove(dataUpload)
                    return (jsonify({"status": 400, "message": f"{check['message']}"}))
        else:
            return (jsonify({"status": 400, "message": "Unsupported filetype"}))
    elif config_check['status'] == "Error":
        jsonify({"status": 400, "message": config_check['message']})
        exit(1)


# def init_cli():
#     os.environ["DB_CONFIG"] = '/home/bob/db/connect/config.yml'
#     parser = argparse.ArgumentParser()
#     inputGroup = parser.add_argument_group("Input")
#     inputGroup.add_argument("-i", "--input", help="Input file name or path. 5 file maximum.",
#                             required=False, nargs='+')
#     outputGroup = parser.add_argument_group("Output")
#     outputGroup.add_argument("-o", "--output", help="Output file name or path.", type=pathlib.Path)
#     outputGroup.add_argument("-f", "--format", help="Output format.", type=ascii,
#                              choices=['xml', 'json', 'csv', 'pdf'])
#     args = parser.parse_args()
#
#     if args.input:
#         validate_file(args.input)
#     elif args.output:
#         file_output(args.output)
#     else:
#         parser.print_help()


if __name__ == "__main__":
    # init_cli()
    initialize()
    app.run(debug=True, port=5001)
