# Pre-installed
import  re
import  os
import  sys
import  time
import  hashlib
import  urllib.parse

# 3rd party
import  pytube
import  rich.console
import  pytube.exceptions

# Globals for quick edits
CON = rich.console.Console()
#                                                                                \/ these options make the mp4 it playable on windows 10
FFMPEG_CMD = f'ffmpeg -i "%s" -i "%s" -map 0:v -map 1:a -c:v copy -shortest "%s" -vcodec libx264 -acodec aac'
RE_YTURL = "(https:\/\/www\.youtube\.com\/watch(&.+?=.+?)*\?v=)?[a-zA-Z0-9_-]{11}(&.+?=.+?)*"

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

def main():
    
    # Ask user for YouTube URL or YouTube video ID
    urlInput = getUserInput("Enter YouTube URL:", lambda i: bool(re.match(RE_YTURL, i)))
    
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
    
    # Check availability of video
    try:
        youtubeObject.check_availability()
    except pytube.exceptions.MembersOnly:
        CON.print("Sorry, this video is exclusive to channel members."); return
    except pytube.exceptions.VideoPrivate:
        CON.print("Sorry, this video is private."); return
    except pytube.exceptions.AgeRestrictedError:
        CON.print("Sorry, this video is age restricted."); return
    except:
        CON.print("Sorry, YouTube won't let you see this video."); return
    
    # Print title and description of video to verify that it's the correct video
    if not getUserInput(
        f"-- Is the video you meant [blue]\"{youtubeObject.title}\"[/] by [blue]\"{youtubeObject.author}\"[/]? [green]y[/]/[red]n[/]",
        lambda i: i.lower().strip() in ["y", "n"]
    ):
        return
    
    # Ask user if audio or video should be downloaded
    downloadType = getUserInput(
        "-- Should video and audio [blue](v)[/] be downloaded or only audio [blue](a)[/]?",
        lambda i: i.lower().strip() in ["v", "a"]
    )
    
    # Ask user for download path
    downloadPath = getUserInput(
        "-- Where should the file be downloaded to?",
        lambda i: os.path.exists( os.path.abspath( i.replace("/", "\\" ) ))
    ).replace("/", "\\")
    downloadPath = os.path.abspath(downloadPath)
    
    # Filter streams into two categories
    audioStreams = [s for s in list(youtubeObject.streams) if s.type == "audio"]
    videoStreams = [s for s in list(youtubeObject.streams) if s.type == "video"]
    
    audioStreams = list({str(a.abr): a for a in audioStreams}.values())
    videoStreams = list({str(v.resolution): v for v in videoStreams}.values())
    
    audioStreams.sort(key = lambda a: -int(str(a.abr)[:-4]))
    videoStreams.sort(key = lambda a: -int(str(a.resolution)[:-1]))

    # Make windows-conform file name from title
    fileName = "".join([char for char in youtubeObject.title if char.isalnum()])
    if len(fileName) >= 200: fileName = fileName[:200]
    
    # Video download consisting of best video AND best audio stream
    if downloadType == "v":
        
        # Find best video stream
        CON.print("-- Please select a video quality:")
        for index, vStream in enumerate(videoStreams):
            CON.print(f"{index + 1}) [blue]{str(vStream.resolution)}[/]")
        
        videoIndex = getUserInput(
            "-- Please enter a number:",
            lambda v: int(v) in list(range(1, len(videoStreams) + 1))
        )
        videoStream = videoStreams[int(videoIndex) - 1]
        
        # Find best audio stream
        CON.print("-- Please select a audio quality:")
        for index, aStream in enumerate(audioStreams):
            CON.print(f"{index + 1}) [blue]{str(aStream.abr)}[/]")
        
        audioIndex = getUserInput(
            "-- Please enter a number:",
            lambda v: int(v) in list(range(1, len(audioStreams) + 1))
        )
        audioStream = audioStreams[int(audioIndex) - 1]
        
        # Download both streams
        CON.print("-- Downloading files.")
        
        # Generate temporary file name with hash
        hash = hashlib.sha1(
            (
                youtubeObject._title +
                str(int(time.time())) # Salt
            ).encode("UTF-8")
        ).hexdigest()[:10]
        tempFileName = f"__temp{hash}__"
        
        # Save temporary files with best video and audio quality
        # mp3
        while True:
            try:
                CON.print(f"-- Downloading \"{tempFileName}.mp3\".")
                audioStream.download(output_path = downloadPath, filename = f"{tempFileName}.mp3")
            except Exception as e:
                if e != KeyboardInterrupt:
                    CON.print(f"-- Encountered Exception: {e}")
                    time.sleep(1)
            except KeyboardInterrupt: break
            else: break
        # mp4
        while True:
            try:
                CON.print(f"-- Downloading \"{tempFileName}.mp4\".")
                videoStream.download(output_path = downloadPath, filename = f"{tempFileName}.mp4")
            except Exception as e:
                if e != KeyboardInterrupt:
                    CON.print(f"-- Encountered Exception: {e}")
                    time.sleep(1)
            except KeyboardInterrupt: break
            else: break

        # Merge temorary mp3 and mp4 with ffmpeg
        CON.print("-- Merging mp3 and mp4.")
        
        print(FFMPEG_CMD % (
            f"{downloadPath}\\{tempFileName}.mp4",
            f"{downloadPath}\\{tempFileName}.mp3",
            f"{downloadPath}\\{fileName}.mp4"
        ))
                
        os.system(FFMPEG_CMD % (
            f"{downloadPath}\\{tempFileName}.mp4",
            f"{downloadPath}\\{tempFileName}.mp3",
            f"{downloadPath}\\{fileName}.mp4"
        ))

        # Delete mp3 and mp4 file
        CON.print("-- Deleting final mp3 file.")
        os.remove(f"{downloadPath}\\{tempFileName}.mp3")
        
        CON.print("-- Deleting final mp4 file.")
        os.remove(f"{downloadPath}\\{tempFileName}.mp4")

        # Make user happy with final message
        CON.print("-- Done saving. Have fun!")
        os.startfile(f"{downloadPath}\\{fileName}.mp4")

    elif downloadType == "a":
        # Find best audio stream
        CON.print("-- Please select a audio quality:")
        for index, aStream in enumerate(audioStreams):
            CON.print(f"{index + 1}) [blue]{str(aStream.abr)}[/]")
        
        audioIndex = getUserInput(
            "-- Please enter a number:",
            lambda v: int(v) in list(range(1, len(audioStreams) + 1))
        )
        audioStream = audioStreams[int(audioIndex) - 1]

        # Download mp3 file
        CON.print("-- Downloading files.")
        audioStream.download(output_path = downloadPath, filename = f"{fileName}.mp3")
        
        # Make user happy with final message
        CON.print("-- Done saving. Opening file. Have fun!")
        os.startfile(f"{downloadPath}\\{fileName}.mp3")

if __name__ == "__main__": main()