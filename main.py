# 1st party
import  re
import  os
import  sys
import  time
import  hashlib
import  subprocess
import  urllib.parse

# 3rd party
import  pytube
import  rich.console
import  pytube.exceptions

# Globals for quick edits
CON = rich.console.Console()
FFMPEG_CMD = f'ffmpeg \
    -loglevel error \
    -i "%s" \
    -i "%s" \
    -map 0:v -map 1:a -c:v copy -shortest "%s" \
    -vcodec libx264 -acodec aac \
'
RE_YTURL = "(https:\/\/www\.youtube\.com\/watch(&.+?=.+?)*\?v=)?[a-zA-Z0-9_-]{11}(&.+?=.+?)*"
DISALLOWED_FILENAME_CHARS = "<>|:\"\\/?*\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f"

def clearLine():
    # Move cursor up one line
    sys.stdout.write("\x1b[1A")
    # Erase line
    sys.stdout.write("\x1b[2K")

def getUserInput(message, verify):
    """ Repeatedly asks the user for an input with the given message
    and only returns result when given function verify(input) returns True. """
    
    while True:
        
        CON.print(message, end = " ")
        userInput = input("")
        
        # Errors and Falsey returns can be used
        try:
            if verify(userInput): break
            else: clearLine()
        except: clearLine()
    
    return userInput

def getQualityChoice(streams, message, qualityAttribute):
    CON.print(message)
    for index, s in enumerate(streams):
        CON.print(f"{index + 1}) [blue]{str(s.__dict__[qualityAttribute])}[/]")
    
    index = getUserInput(
        "<< Please enter a number:",
        lambda v: int(v) in list(range(1, len(streams) + 1))
    )
    
    stream = streams[int(index) - 1]
    return stream

def download(stream, message, downloadPath, filename):
    while True:
        try:
            CON.print(message)
            stream.download(output_path = downloadPath, filename = filename)
        except Exception as e:
            if e != KeyboardInterrupt:
                CON.print(f"-- Encountered Exception: {e}")
                time.sleep(1)
        except KeyboardInterrupt: return 1
        else: return 0

def main():
    
    # Ask user for YouTube URL or YouTube video ID
    urlInput = getUserInput("<< Enter YouTube URL or video ID:", lambda i: bool(re.match(RE_YTURL, i)))
    
    # If theres more than the id, filter for id
    if len(urlInput) != 11:
        
        # Parse URL to get URL parameters
        urlObject = urllib.parse.urlparse(urlInput)
        
        # Get id from query
        queries = urlObject.query.split("&")
        for query in queries:
            if query.startswith("v="): videoId = query.split("=")[1]
    
    else:
        videoId = urlInput
    
    # Get video object
    youtubeObject = pytube.YouTube(f"https://www.youtube.com/watch?v={videoId}")
    
	# Print title and description of video to verify that it's the correct video
    if not getUserInput(
        f"<< Is the video you meant [blue]\"{youtubeObject.title}\"[/] by [blue]\"{youtubeObject.author}\"[/]? [green]y[/]/[red]n[/]",
        lambda i: i.lower().strip() in ["y", "n"]
    ):
        return

    CON.print("-- Checking video availability...")
    # Check availability of video
    try:
        youtubeObject.check_availability()
    except Exception as e:
        match e:
            case pytube.exceptions.MembersOnly:
                CON.print(">> [red]Sorry, this video is exclusive to channel members.[/]")
            case pytube.exceptions.VideoPrivate:
                CON.print(">> [red]Sorry, this video is private.[/]")
            case pytube.exceptions.AgeRestrictedError:
                CON.print(">> [red]Sorry, this video is age restricted.[/]")
            case _:
                CON.print(">> [red]Sorry, YouTube won't let you see this video.[/]")
        
        main()
        return
    
    # Ask user if audio or video should be downloaded
    downloadType = getUserInput(
        "<< Should video and audio [blue](va)[/] be downloaded or only video [blue](v)[/] only audio [blue](a)[/]?",
        lambda i: i.lower().strip() in ["va", "v", "a"]
    )
    
    # Ask user for download path
    downloadPath = getUserInput(
        "<< Where should the file be downloaded to?",
        lambda i: os.path.exists( os.path.abspath( i.replace("/", "\\" ) ))
    ).replace("/", "\\")
    downloadPath = os.path.abspath(downloadPath)
    
    print(youtubeObject)

    # Filter streams into two categories
    audioStreams = [s for s in list(youtubeObject.streams) if s.type == "audio"]
    videoStreams = [s for s in list(youtubeObject.streams) if s.type == "video"]
    
    audioStreams = list({str(a.abr): a for a in audioStreams}.values())
    videoStreams = list({str(v.resolution): v for v in videoStreams}.values())
    
    audioStreams.sort(key = lambda a: -int(str(a.abr)[:-4]))
    videoStreams.sort(key = lambda a: -int(str(a.resolution)[:-1]))
    
    # Make windows-conform file name from title
    fileName = "".join([ char if char not in DISALLOWED_FILENAME_CHARS else "_" for char in youtubeObject.title ])
    if len(fileName) >= 200: fileName = fileName[:200]
    
    # Video download consisting of best video AND best audio stream
    if downloadType == "va":
        
        # Find streams of user's choice
        videoStream = getQualityChoice(videoStreams, "<< Please select a video quality:", "resolution")
        audioStream = getQualityChoice(audioStreams, "<< Please select a audio quality:", "abr")
        
        # Download both
        CON.print("-- Downloading files.")
        
        # Generate temporary file name with hash
        hash = hashlib.sha1(
            (
                youtubeObject._title + # Hash Base
                str(int(time.time())) # Salt
            ).encode("UTF-8")
        ).hexdigest()[:10] # Simple 10 hex digits
        tempFileName = f"__temp{hash}__"
        
        # Save temporary files with best video and audio quality
        # mp3
        c1 = download(audioStream, f"-- Downloading \"{tempFileName}.mp3\".", downloadPath, f"{tempFileName}.mp3")
        # delete file again if user ctrl-c'd
        if c1 == 1:
            os.remove(os.path.join(downloadPath, f"{tempFileName}.mp3"))
            return
        
        # mp4
        c2 = download(videoStream, f"-- Downloading \"{tempFileName}.mp4\".", downloadPath, f"{tempFileName}.mp4")
        # delete file again if user ctrl-c'd
        if c2 == 1:
            os.remove(os.path.join(downloadPath, f"{tempFileName}.mp3"))
            os.remove(os.path.join(downloadPath, f"{tempFileName}.mp4"))
            return

        # Merge temorary mp3 and mp4 using ffmpeg
        CON.print("-- Merging mp3 and mp4.")
        
        subprocess.run(FFMPEG_CMD % (
            f"{downloadPath}\\{tempFileName}.mp4",
            f"{downloadPath}\\{tempFileName}.mp3",
            f"{downloadPath}\\{fileName}.mp4"
        ), stdout = subprocess.DEVNULL)

        # Delete mp3 and mp4 file
        CON.print("-- Deleting final mp3 file.")
        os.remove(f"{downloadPath}\\{tempFileName}.mp3")
        
        CON.print("-- Deleting final mp4 file.")
        os.remove(f"{downloadPath}\\{tempFileName}.mp4")

        # Make user happy with final message
        CON.print(">> Done saving. Opening file. Have fun!")
        os.startfile(f"{downloadPath}\\{fileName}.mp4")

    elif downloadType == "v":
        # Find best audio stream
        CON.print("<< Please select a video quality:")
        for index, vStream in enumerate(videoStreams):
            CON.print(f"{index + 1}) [blue]{str(vStream.resolution)}[/]")
        
        videoIndex = getUserInput(
            "<< Please enter a number:",
            lambda v: int(v) in list(range(1, len(videoStreams) + 1))
        )
        videoStream = videoStreams[int(videoIndex) - 1]

        # Download mp3 file
        CON.print("-- Downloading files.")
        videoStream.download(output_path = downloadPath, filename = f"{fileName}.mp4")
        
        # Make user happy with final message
        CON.print(">> Done saving. Opening file. Have fun!")
        os.startfile(f"{downloadPath}\\{fileName}.mp4")

    elif downloadType == "a":
        # Find best audio stream
        CON.print("<< Please select a audio quality:")
        for index, aStream in enumerate(audioStreams):
            CON.print(f"{index + 1}) [blue]{str(aStream.abr)}[/]")
        
        audioIndex = getUserInput(
            "<< Please enter a number:",
            lambda v: int(v) in list(range(1, len(audioStreams) + 1))
        )
        audioStream = audioStreams[int(audioIndex) - 1]

        # Download mp3 file
        CON.print("-- Downloading files.")
        audioStream.download(output_path = downloadPath, filename = f"{fileName}.mp3")
        
        # Make user happy with final message
        CON.print(">> Done saving. Opening file. Have fun!")
        os.startfile(f"{downloadPath}\\{fileName}.mp3")

if __name__ == "__main__": main()
