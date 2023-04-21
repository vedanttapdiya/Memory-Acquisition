#!/usr/bin/env python
import sys
import subprocess
import os
from datetime import datetime
import time
import psutil
import platform
import hashlib

# get the current working directory
cwd = os.getcwd()
output = f"{cwd}/Output/"


reset = False
file_path = ""


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def detect_os():
    """Detect the current operating system"""
    global startupinfo, system_model, command, system_manufacturer, os_build
    os_build = ""
    if sys.platform.startswith('win'):
        import wmi
        c = wmi.WMI()
        system_manufacturer = c.Win32_ComputerSystem()[0].Manufacturer
        system_model = c.Win32_ComputerSystem()[0].Model
        os_build = c.Win32_OperatingSystem()[0].BuildNumber

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        command = [resource_path('tools/winpmem_mini_x64_rc2.exe')]
        return 'Windows'
    elif sys.platform.startswith('linux'):
        try:
            output = subprocess.check_output(['dmidecode', '-t', 'system'], stderr=subprocess.DEVNULL)
            output = output.decode('utf-8').split('\n')
            for line in output:
                if 'Manufacturer' in line:
                    system_manufacturer = line.split(': ')[1].strip()
                elif 'Product Name' in line:
                    system_model = line.split(': ')[1].strip()
        except Exception as e:
            print("Error retrieving system information using dmidecode:", str(e))
            print("Falling back to platform.uname().machine.")
            system_manufacturer = ''
            system_model = platform.uname().machine

        startupinfo = None
        command = ['./tools/avml-minimal']
        return 'Linux'
    elif sys.platform.startswith('darwin'):
        try:
            output = subprocess.check_output(['system_profiler', 'SPHardwareDataType'], stderr=subprocess.DEVNULL)
            output = output.decode('utf-8').split('\n')
            for line in output:
                if 'Model Name' in line:
                    system_model = line.split(': ')[1].strip()
        except Exception as e:
            print("Error retrieving system information using system_profiler:", str(e))
            print("Falling back to platform.uname().machine.")
            system_model = platform.uname().machine

        system_manufacturer = "Apple Inc."
        startupinfo = None
        command = None
        return 'Mac OS'
    else:
        raise OSError("Unsupported operating system")


def get_dump_file_path(filefmt_choice, specified_filename):
    """Create a file path with current date and time"""
    global file_name
    global formatted_date
    global Report_file
    os.makedirs("Output", exist_ok=True)
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    formatted_date = datetime.now().strftime("%A %d %B %Y %H:%M:%S")

    if specified_filename:
        file_name = specified_filename
    else:
        file_name = f"memdump_{current_time}"

    # File path with date and time stamp
    Report_file = f'Output/Report_{file_name}.txt'
    file_path = output + file_name + filefmt_choice
    return file_path


os_name = detect_os()
print(command)


def dump_ram(file_path):
    """Dump the contents of RAM to a file."""
    process = subprocess.Popen(
        command + [file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)

    while process.poll() is None:
        if reset:
            process.kill()
        time.sleep(0.1)


# Labels and entries for Case Details
case_details = {
    "Case Number": "",
    "Case Name": "",
    "Case Description": ""
}

# Labels and entries for Examiner Details
examiner_details = {
    "Name": "",
    "Phone Number": "",
    "Email Id": "",
    "Organization": ""
}

# Insert your report creation function here
elapsed_time = ""
end_time = ""

hash_result = {}

# Function to calculate the hash of a file
def calculate_file_hash(result, hash_algorithm, filename):
    """
    Calculate the hash of a file using the specified hash algorithm.
    :param filename: The name of the file to calculate the hash for.
    :param hash_algorithm: The hash algorithm to use. Default is "sha256".
    :return: The hash value as a hexadecimal string.
    """
    try:
        # Open the file in binary mode for reading
        with open(filename, 'rb') as file:
            # Create the hash object
            hash_obj = hashlib.new(hash_algorithm)

            # Read the file in chunks to avoid memory issues
            chunk_size = 4096
            while True:
                data = file.read(chunk_size)
                if not data:
                    break
                hash_obj.update(data)

            # Return the hexadecimal representation of the hash
            result[hash_algorithm] = hash_obj.hexdigest()
    except FileNotFoundError:
        print(f"File '{filename}' not found.")
    except PermissionError:
        print(f"Permission denied to read file '{filename}'.")
    except Exception as e:
        print(f"Error while calculating hash for file '{filename}': {e}")

def generate_report(filefmt_choice):
    os.makedirs("Output", exist_ok=True)
    open(Report_file, 'w').write('')

    system_name = platform.node()
    system_architecture = platform.architecture()[0]

    os_name = platform.system()
    os_version = platform.version()

    total_physical_memory = f"{psutil.virtual_memory().total / 1024**3:.2f} GB"
    total_virtual_memory = f"{psutil.swap_memory().total / 1024**3:.2f} GB"
    report_template = """
--------------xx Memory Acquisition Report xx--------------
Report Created By 4n6 Memory Acquisition Tool v1.0
-----------------------------------------------------------

[Case Details:]
    Number:      {case_number}
    Name:        {case_name}
    Description: {case_description}
    
[Examiner Details:]
    Name:         {examiner_name}
    Phone No.:    {examiner_phone}
    Email Id:     {examiner_email}
    Organization: {examiner_organization}

-----------------------------------------------------------

[Dump File Information:]

	File Name: {file_name}
	File Format: {specified_file_format}
	File Size: {file_size} GB
	File Location: {file_path}

	MD5 Hash: {md5_hash}
	SHA1 Hash: {sha1_hash}
	SHA256 Hash: {sha256_hash}

-----------------------------------------------------------

[Acquisition Details:]
	
	Start Time: {current_time}
	End Time: {end_time}
	Elapsed Time: {elapsed_time}

-----------------------------------------------------------

[Target Device Information:]

    System Name: {system_name}
    System Manufacturer: {system_manufacturer}
    System Model: {system_model}
    System Architecture: {system_architecture}

    OS Name: {os_name}
    OS Version: {os_version}
    OS Build: {os_build}

    Total Physical Memory: {total_physical_memory}
    Total Virtual Memory: {total_virtual_memory}

-----------------------------------------------------------
        """

    report = report_template.format(
        case_number=case_details["Case Number"],
        case_name=case_details["Case Name"],
        case_description=case_details["Case Description"],
        examiner_name=examiner_details["Name"],
        examiner_phone=examiner_details["Phone Number"],
        examiner_email=examiner_details["Email Id"],
        examiner_organization=examiner_details["Organization"],
        system_name=system_name,
        system_manufacturer=system_manufacturer,
        system_model=system_model,
        system_architecture=system_architecture,
        os_name=os_name,
        os_version=os_version,
        os_build=os_build,
        total_physical_memory=total_physical_memory,
        total_virtual_memory=total_virtual_memory,
        file_name=file_name,
        file_path=file_path,
        specified_file_format=filefmt_choice,
        file_size=(os.path.getsize(file_path)/1024 ** 3),
        md5_hash=hash_result["md5"],
        sha1_hash=hash_result["sha1"],
        sha256_hash=hash_result["sha256"],
        current_time=formatted_date,
        end_time=end_time,
        elapsed_time=elapsed_time,
    )

    with open(Report_file, "w") as f:
        f.write(report)


if __name__ == "__main__":
    dump_ram(file_path)
