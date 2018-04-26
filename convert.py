#!/usr/bin/python

import sys
import os
import subprocess
import tempfile
import uuid
import shutil
import pyinotify

watchDir = '/encode'
mediatypes = ('.mkv', '.mp4')

def convert(paths):
    print('Starting')
    print(isinstance(paths, list))
    if isinstance(paths, list):
        if len(paths) == 0:
            paths = [watchDir]
        paths = getMediaFiles(paths)
    else:
        paths = [paths]
    paths = filterForConvertion(paths)
    if len(paths) != 0:
        convertFiles(paths)
    print('Done!')

def getMediaFiles(paths):
    print('Scan for media files')
    mediafiles = []
    for path in paths:
        if not os.path.exists(path):
            print('path', path, 'did not exist')
            continue

        if os.path.isfile(path):
            if path.lower().endswith(mediatypes):
                mediafiles.append(path)
        else:
            for root, subdirs, files in os.walk(path):
                for file in files:
                    path = root + "/" + file
                    if path.lower().endswith(mediatypes):
                        mediafiles.append(path)

    lenAll = len(mediafiles)
    # Remove duplicate paths
    mediafiles = list(set(mediafiles))
    lenDup = len(mediafiles)
    print ("{} files scanned ({} duplicates)".format(lenAll, lenAll-lenDup))
    return mediafiles

def filterForConvertion(paths):
    print('Filter for convertion')
    filteredForConvert = []
    for path in paths:
        cmd = "ffprobe -loglevel panic -select_streams a:0 -show_entries stream=codec_name,channels -of default=noprint_wrappers=1:nokey=1 \""+path+"\""
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        p.wait()
        output = p.stdout.read().rstrip().decode('utf-8')
        if not output:
            continue
        acodec, channels =output.split()[0:2]
        if acodec != "aac" or int(channels) > 2:
            filteredForConvert.append(path)
    # Remove duplicate paths
    filteredForConvert = list(set(filteredForConvert))
    print ("{} files ready for convertion".format(len(filteredForConvert)))
    return filteredForConvert

def convertFiles(paths):
    print("Start convert")
    temppath = os.path.join(tempfile.gettempdir(), "audioconvert")
    if not os.path.exists(temppath):
        os.makedirs(temppath)

    for idx, path in enumerate(paths):
        tempfilepath = os.path.join(temppath,str(uuid.uuid4())+ os.path.splitext(path)[1])

        cmd="ffmpeg -i \""+path+"\" -c:v copy -ac 2 -c:a aac -b:a 128k \""+tempfilepath+"\" -y"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,universal_newlines=True)
        #p.wait()
        duration = 0
        while True:
            line = p.stdout.readline()
            if not line:
                break
            if 'Duration: ' in line:
                duration = convertToTime(line.split('Duration: ')[1].split(',')[0])
            if 'time=' in line:
                time = convertToTime(line.split('time=')[1].split(' ')[0])
                percent = str(int((time / duration) * 100))
                print('\r{} of {} - ({}%) {}'.format(idx+1, len(paths), percent, path), end='')
        #print('{} of {} - {}'.format(idx+1, len(paths), path))
        shutil.move(tempfilepath, path)
    print('') #newline
    shutil.rmtree(temppath)

def convertToTime(t):
    ms = 0
    t, _ms = t.split('.')
    ms += int(_ms)
    h, m, s = t.split(':')
    ms += int(s)*100
    ms += int(m)*100*60
    ms += int(h)*100*60*60
    return ms

class EventHandler(pyinotify.ProcessEvent):
    def process_default(self, event):
        if not event.dir:
            convert(event.pathname)

if __name__ == "__main__":
    if len(sys.argv) != 1:
        convert(sys.argv[1:])
    else:
        wm = pyinotify.WatchManager()
        handler = EventHandler()
        notifier = pyinotify.Notifier(wm, handler)
        wm.add_watch(watchDir, pyinotify.IN_CREATE, rec=True, auto_add=True)
        notifier.loop()

