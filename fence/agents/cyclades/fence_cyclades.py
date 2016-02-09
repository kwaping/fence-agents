#!/usr/bin/python -tt

#####
##
## The Following Agent Has Been Tested On:
##
##  Model       Firmware
## +---------------------------------------------+
##  
##  
#####

import sys, re
import atexit
sys.path.append("@FENCEAGENTSLIBDIR@")
from fencing import *
from fencing import fail, fail_usage, EC_STATUS

#BEGIN_VERSION_GENERATION
RELEASE_VERSION="Cyclades Agent"
REDHAT_COPYRIGHT=""
BUILD_DATE="January, 2016"
#END_VERSION_GENERATION

def get_outlet_list(conn,options):
	conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))


def get_power_status(conn, options):
	exp_result = 0
	outlets = {}

	conn.send_eol("1")
	conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))

	version = 0
	admin = 0
	switch = 0

	if None != re.compile('.* MasterSwitch plus.*', re.IGNORECASE | re.S).match(conn.before):
		switch = 1
		if None != re.compile('.* MasterSwitch plus 2', re.IGNORECASE | re.S).match(conn.before):
			if not options.has_key("--switch"):
				fail_usage("Failed: You have to enter physical switch number")
		else:
			if not options.has_key("--switch"):
				options["--switch"] = "1"

	if None == re.compile('.*Outlet Management.*', re.IGNORECASE | re.S).match(conn.before):
		version = 2
	else:
		version = 3

	if None == re.compile('.*Outlet Control/Configuration.*', re.IGNORECASE | re.S).match(conn.before):
		admin = 0
	else:
		admin = 1

	if switch == 0:
		if version == 2:
			if admin == 0:
				conn.send_eol("2")
			else:
				conn.send_eol("3")
		else:
			conn.send_eol("2")
			conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))
			conn.send_eol("1")
	else:
		conn.send_eol(options["--switch"])

	while True:
		exp_result = conn.log_expect(
				["Press <ENTER>"] + options["--command-prompt"], int(options["--shell-timeout"]))
		lines = conn.before.split("\n")
		show_re = re.compile(r'(^|\x0D)\s*(\d+)- (.*?)\s+(ON|OFF)\s*')
		for line in lines:
			res = show_re.search(line)
			if res != None:
				outlets[res.group(2)] = (res.group(3), res.group(4))
		conn.send_eol("")
		if exp_result != 0:
			break
	conn.send(chr(03))
	conn.log_expect("- Logout", int(options["--shell-timeout"]))
	conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))

	if ["list", "monitor"].count(options["--action"]) == 1:
		return outlets
	else:
		try:
			(_, status) = outlets[options["--plug"]]
			return status.lower().strip()
		except KeyError:
			fail(EC_STATUS)

def set_power_status(conn, options):
	action = {
		'on' : "1",
		'off': "2"
	}[options["--action"]]

	conn.send_eol("1")
	conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))

	version = 0
	admin2 = 0
	admin3 = 0
	switch = 0

	if None != re.compile('.* MasterSwitch plus.*', re.IGNORECASE | re.S).match(conn.before):
		switch = 1
		## MasterSwitch has different schema for on/off actions
		action = {
			'on' : "1",
			'off': "3"
		}[options["--action"]]
		if None != re.compile('.* MasterSwitch plus 2', re.IGNORECASE | re.S).match(conn.before):
			if not options.has_key("--switch"):
				fail_usage("Failed: You have to enter physical switch number")
		else:
			if not options.has_key("--switch"):
				options["--switch"] = 1

	if None == re.compile('.*Outlet Management.*', re.IGNORECASE | re.S).match(conn.before):
		version = 2
	else:
		version = 3

	if None == re.compile('.*Outlet Control/Configuration.*', re.IGNORECASE | re.S).match(conn.before):
		admin2 = 0
	else:
		admin2 = 1

	if switch == 0:
		if version == 2:
			if admin2 == 0:
				conn.send_eol("2")
			else:
				conn.send_eol("3")
		else:
			conn.send_eol("2")
			conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))
			if None == re.compile('.*2- Outlet Restriction.*', re.IGNORECASE | re.S).match(conn.before):
				admin3 = 0
			else:
				admin3 = 1
			conn.send_eol("1")
	else:
		conn.send_eol(options["--switch"])

	while 0 == conn.log_expect(
			["Press <ENTER>"] + options["--command-prompt"], int(options["--shell-timeout"])):
		conn.send_eol("")

	conn.send_eol(options["--plug"]+"")
	conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))

	if switch == 0:
		if admin2 == 1:
			conn.send_eol("1")
			conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))
		if admin3 == 1:
			conn.send_eol("1")
			conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))
	else:
		conn.send_eol("1")
		conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))

	conn.send_eol(action)
	conn.log_expect("Enter 'YES' to continue or <ENTER> to cancel :", int(options["--shell-timeout"]))
	conn.send_eol("YES")
	conn.log_expect("Press <ENTER> to continue...", int(options["--power-timeout"]))
	conn.send_eol("")
	conn.log_expect(options["--command-prompt"], int(options["--power-timeout"]))
	conn.send(chr(03))
	conn.log_expect("- Logout", int(options["--shell-timeout"]))
	conn.log_expect(options["--command-prompt"], int(options["--shell-timeout"]))

def main():
	device_opt = ["ipaddr", "login", "passwd", "cmd_prompt", "secure", \
			"port", "switch", "telnet"]

	atexit.register(atexit_handler)

	all_opt["cmd_prompt"]["default"] = ["\npm>", "\n>"]
	all_opt["ssh_options"]["default"] = "-1 -c blowfish"

	options = check_input(device_opt, process_input(device_opt))

	docs = {}
	docs["shortdesc"] = "Fence agent for Cyclades over telnet/ssh"
	docs["longdesc"] = "fence_cyclades is an I/O Fencing agent \
which can be used with the Cyclades network power switch. It logs into device \
via telnet/ssh  and reboots a specified outlet. Lengthy telnet/ssh connections \
should be avoided while a GFS cluster  is  running  because  the  connection \
will block any necessary fencing actions."
	docs["vendorurl"] = "http://www.emersonnetworkpower.com"
	show_docs(options, docs)

	## Support for --plug [switch]:[plug] notation that was used before
	if (options.has_key("--plug") == 1) and (-1 != options["--plug"].find(":")):
		(switch, plug) = options["--plug"].split(":", 1)
		options["--switch"] = switch
		options["--plug"] = plug

	##
	## Operate the fencing device
	####
	conn = fence_login(options, re_login_string=r"(^$)|(Username:\s*)")

    result = fence_action(conn, options, set_power_status, get_power_status, get_outlet_list)

	fence_logout(conn, "exit")
    conn.close()
	sys.exit(result)

if __name__ == "__main__":
	main()
