#!/usr/bin/python3
# -*- coding: UTF-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os, os.path
import sys
import tempfile
import datetime, time
import subprocess
import re
from multiprocessing import Process, Queue, Semaphore



def parse_dependancies(filepath, q_compile, parse_lock, freq=1):
    """
    Parse all dependacies included in latex files
    """
    latex_filename = filepath+'.tex'
    tree = []
    reset = False
    cycle = 0
    while 1:
        if not parse_lock.get_value():
            time.sleep(freq)
            continue
        cycle += 1


        if not os.path.exists(filepath+'.log'):
            q_compile.put('Compilation in process...')
            time.sleep(freq)
            continue
        else:
            comp_time = os.path.getmtime(filepath+'.log')
        #print cycle

        for idx in range(len(tree)):
            # check for file changes 
            tree[idx]['mtime'] = os.path.getmtime(tree[idx]['path'])

        if not tree or (cycle % 10 == 0): 
            # reparse the whole tree if not defined and every N cycles
            # for good measure
            tree_old = tree
            tree = [dict(path=latex_filename, 
                     command='root',
                     checked=True,
                     mtime=os.path.getmtime(latex_filename))]
            tree.extend(parse_latex(latex_filename)) # parse dependancies of the main file
            while not all([el['checked'] for el in tree]):
                # look for higher lever dependacies (multiple includes)
                # not tested at all
                cel = filter(lambda el: not el['checked'], tree)[0]
                cel['checked'] = True
                tmp_tree = parse_latex(cel['path'])
                for el in tmp_tree:
                    if el not in tree:
                        tree.append(el)
        

        if any([el['mtime'] > comp_time for el in tree]):
            print("Files changes detected:")
            for el in tree:
                if el['mtime'] > comp_time:
                    print('   -', el['path'])
            q_compile.put('compiling...')
        if not freq:
            break
        time.sleep(freq)
    return tree

def parse_latex(filename):
    """
    Parse a latex file for dependencies
    """
    regexp = (r'\\(?P<command>input|include|includegraphics)'   # command name
        r'(?:\[[^]]+\])?' # optional arguments [*]
        r'{(?P<path>[^}]+)}'   # file name {*} 
        )
    slist = []

    with open(filename, 'r') as f:
        for line in f:
            if re.match(r'^\s*%.*$', line):
                continue # ignore lines with comments
            match = re.search(regexp, line)
            if match:
                slist.append(
                        {key : match.group(key) for key in ['command', 'path']})
                if not os.path.splitext(match.group('path'))[1]:
                    slist[-1]['path'] += '.tex'
                mpath = slist[-1]['path']
                if os.path.exists(mpath):
                    slist[-1]['mtime'] = os.path.getmtime(mpath)
                else:
                    slist[-1]['mtime'] = None
                #if os.path.splitext("img/Bdot_image.jpg")[1] in ['.tex']:
                #    slist[-1]['checked'] = False
                #else:
                slist[-1]['checked'] = True
    return slist


def recompile(latex_main, q_compile, parse_lock, command='pdflatex', freq=1, ):
    while True: 
        if q_compile.empty():
            time.sleep(freq)
            continue

        target = q_compile.get()
        parse_lock.acquire()
        print(target)


        out = tempfile.TemporaryFile()
        out2 = tempfile.TemporaryFile()
        t =  time.time()
        if command is 'latex':
            ec = subprocess.call(
                ["latex", "-halt-on-error", latex_main], stdout = out)
            ec2 = subprocess.call(
                    ["dvipdfm",latex_main+'.dvi'],stdout = out2)
        elif command in ['pdflatex', 'xelatex']:
            ec = subprocess.call(
                [command, "-halt-on-error", "-shell-escape",
                    latex_main], stdout = out)
        else:
            print('Unknown argument {0}'.format(command))

        if ec:
            if out:
                out.seek(0)
                sys.stdout.write(out.read())
            print("auptex: ERROR generating {} with xelatex in {:.1f}s.".format(latex_main, time.time() - t))
        else:
            print("auptex: Successfully generated {} in {:.1f}s.".format(latex_main,
                    time.time() - t))
        if out:
            out.close()
        parse_lock.release()


def cli():

    import argparse

#========================  Argument parser  ==============================#

    parser = argparse.ArgumentParser(description= """
            Automatically recompile latex documents when files are updated
    """)
    parser.add_argument('inputfile',
            action="store", type=str,
            help='Working latex file')
    parser.add_argument('-c','--compiler',
            action="store", type=str,
            default='pdflatex',
            help='Compile using latex and dvipdfm')
    parser.add_argument('-a','--action',
            action="store", type=str,
            default='compile',
            help='What action to do')
    args = parser.parse_args()

    latex_filename = os.path.abspath(args.inputfile)
    if not os.path.exists(latex_filename):
        print('Error: file {} does not exist'.format(latex_filename))
        sys.exit(0)
    latex_dir, latex_name = os.path.split(latex_filename)
    latex_name = os.path.splitext(latex_name)[0]
    os.chdir(latex_dir)
    latex_dir =  os.path.split(latex_dir)[1]
    q_compile = Queue()
    parse_lock = Semaphore()

    if args.action == 'compile':
        p_parse = Process(target=parse_dependancies,
                args=(latex_name, q_compile, parse_lock))
        p_compile = Process(target=recompile,
                args=(latex_name, q_compile, parse_lock, args.compiler))
        p_parse.start()
        p_compile.start()
    elif args.action == 'zip':
        import zipfile
        print("Creating a zip archive")
        tree =  parse_dependancies(latex_name, q_compile, parse_lock, freq=0)
        os.chdir("../")
        with zipfile.ZipFile('{0}.zip'.format(latex_dir), 'w') as zf:
            for leaf in tree:
                zf.write(os.path.join('{0}'.format(latex_dir), leaf['path']))
            #zf.write(os.path.join('{0}'.format(latex_dir), "poster_CosmoB.bib"))


    #p_parse.join()


