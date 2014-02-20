#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
	Parse nagios object configure and status files, which are plain text document

"""

import os
import re
from collections import defaultdict
from copy import deepcopy
from pprint import pprint

COMMENT_FLAGS = '#;' # characters , indicate notes
BLOCK_FLAGS = '{}' # character pair , indicate a block
ITEM_SPLIT = '= \t' # characters, split a item line to key and value

def core_parse(fpath):
	''' todo: add parammeter strict means error raise Error
	           ignore or replace means try handle no raise 
	'''
	
	status = -1
	next_status = {-1:[0],0:[1],1:[1,2],2:[0]}
	line_regs = ( '^(\w+)(\s+\w+)?\s*%s$' % (BLOCK_FLAGS[0], ), 
				'^[^%s]+$' % (BLOCK_FLAGS,),
				'^\s*%s$' % (BLOCK_FLAGS[1],),
				)
	linenum = 0
	blocks = defaultdict(list)
	
	fd = open(fpath)
	if os.path.getsize(fpath) < 10485760: # 10MiB
		lines = fd.readlines()
		fd.close()
	else:
		lines = fd
	
	for rawline in lines:
		linenum += 1
		# clear empty line or comment line
		line = rawline.strip()
		if not line or line[0] in COMMENT_FLAGS :
			continue
		# clear comment in line
		match_note = re.search('[%s]' % (COMMENT_FLAGS,), line )
		if match_note:
			line = line[:match_note.start()].strip()
		# check line
		for i, reg in enumerate(line_regs):
			match_line = re.search(reg, line)
			if not match_line:
				continue
			need_status = next_status[status]
			if i not in need_status:
				raise ValueError, 'line %d error[status:%d:%s][%s]' % (linenum,i,
					str(need_status)[1:-1],line)
			status = i
			if status == 0:
				names = [x.strip() for x in match_line.groups() if x]
				block = {'name': names[-1],'items' : {} }
			elif status == 1:
				items = re.split('[%s]' % (ITEM_SPLIT,), line)
				key = items[0]
				value = line[len(key):].strip().lstrip(ITEM_SPLIT)
				block['items'][key] = value
			else:
				blocks[block['name']].append(block['items'])
			break # do not try other line regex
		else:
			raise ValueError, 'line %d error[unknown][%s]' % (linenum,line)
	
	if not fd.closed:
		fd.close()
	return dict(blocks)

def parse_status(fpath):
	return core_parse(fpath)

def parse_with_template(fpath, template = None ):
	'parse objects which use or not use template'

	def _merge(cur, category,cur_template):
		cur_beuse = beuse = cur_template[category][cur['use']]
		allused = set() # check Circle require
		while cur_beuse:
			if cur_beuse['name'] in allused:
				raise ValueError,'Cycle dependency'
			allused.add( cur_beuse['name'] )
			if 'use' not in cur_beuse:
				break
			else:
				cur_beuse = cur_template[category][cur_beuse['use']]
		if 'use' in beuse:
			_merge(beuse, category, cur_template)

		for k, v in beuse.iteritems():
			if k not in cur and k != 'name': # template name useless
				cur[k] = v
		if 'use' in cur:
			del cur['use']

	def inittemplate(result, idata):
		for category, value in idata.iteritems():
			if category not in result:
				result[category] = {}
			items = [value] if isinstance(value, dict) else value
			for item in items:
				if 'name' in item:
					if item['name'] not in result[category]:
						result[category][item['name']] = item
					else:
						# error or merge
						raise ValueError , 'duplicate define[%s]' % (item['name'],)

	if not fpath:
		return {}
	
	if not template:
		template = {}
	elif not isinstance(template,dict):
		raise ValueError,'template must be dictionary type'

	dicttemplate = {} # dictionary in dictionary

	inittemplate(dicttemplate, template)
	
	# maybe some template is in data file, find and use them
	data = core_parse(fpath)
	inittemplate(dicttemplate, data)
	
	# merge all template according their 'use'
	end_template = {}
	for category, items in dicttemplate.iteritems(): # type name, items(dictionary type)
		end_template[category] = {}
		for keyname , one in items.iteritems(): # every template has a name
			if 'use' in one:
				if one['use'] not in dicttemplate[category]: # use a not exists template
					del one['use']
				else:
					_merge(one,category,dicttemplate )
			end_template[category][keyname] = one

	# merge data and end_template
	end_data = {}
	for category, items in data.iteritems():
		end_data[category] = []
		for item in items:
			if 'use' in item:
				if item['use'] not in end_template[category]:
					raise ValueError, 'file[%s] use a not exists template[%s]' % (fpath,item['use'])
				else:
					_merge(item, category, end_template)
			end_data[category].append(item)
	return end_data

def parse_objects(fpath, template_path = None):
	template = parse_with_template(template_path)
	return parse_with_template(fpath, template)


def test_objects():
	dpath = '/home/xiowei/download/tar/nagios-4.0.2/sample-config/template-object'


	pt = dpath + '/templates.cfg.in'
	ph = dpath + '/localhost.cfg.in'

	pprint( parse_objects(ph, pt) )

def main():
	data = parse_status('/home/xiowei/tmp/status.dat')
	pprint(data)

if __name__ == '__main__':
	test_objects()
	pprint('End')
