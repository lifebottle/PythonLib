import httplib2
import os
from oauth2client import client, tools,file
import base64
from email import encoders
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from apiclient import errors, discovery
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

def get_credentials(): # Gets valid user credentials from disk.
    SCOPES = 'https://www.googleapis.com/auth/gmail.send'
    CLIENT_SECRET_FILE = os.path.join( os.getcwd(), "..",'client_secrets.json')
    APPLICATION_NAME = 'Gmail API Python Send Email'

    credential_path = os.path.join( os.getcwd(), "..",
                                   'gmail-python-email-send.json')

    store = file.Storage(credential_path)
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        #if flags:
        credentials = tools.run_flow(flow, store)

    return credentials


def send_message(sender, to, commiter_name, subject, xdelta_link):
    
    
    message_text = """
Hi {},

here is your xdelta patch : 
{}
""".format(commiter_name, xdelta_link)

    credentials = get_credentials()
    #print (credentials)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('gmail', 'v1', http=http)
    message1 = create_message(sender, to,subject, message_text)
    send_message_internal(service, "me", message1)

def send_message_internal(service, user_id, message):
    """Send an email message.

        Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        message: Message to be sent.

        Returns:
        Sent Message.
    """
    try:
        message = (service.users().messages().send(userId=user_id, body=message)
                   .execute())
        # print('Message Id: %s' % message['id'])
        return message
    except errors.HttpError as error:
        print('An error occurred: %s' % str(error)[0:200])

def create_message(
    sender, to, subject, message_text):
    """Create a message for an email.

    Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.
    file: The path to the file to be attached.

    Returns:
    An object containing a base64url encoded email object.
    """
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    msg = MIMEText(message_text, 'html')
    message.attach(msg)

    #filename = os.path.basename(file)
    #msg.add_header('Content-Disposition', 'attachment', filename=filename)
    #message.attach(msg)

    return {'raw': base64.urlsafe_b64encode(str(message).encode('UTF-8')).decode('ascii')}
    # return {'raw': base64.urlsafe_b64encode(message.as_string())}




###Google Drive stuff
def get_file(drive, file_name, folder_name):
    
    folder_id = get_folder(drive, folder_name)
    
    file_name = os.path.basename(file_name)
    file_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(folder_id)}).GetList()
    
    file = [file for file in file_list if file['title'] == file_name]
    if len(file) > 0:
        
        return file[0]
    else:
        print("File not found in gdrive folder")
    
def get_folder(drive, folder_name):

    parent_id = '1xbDBJLg4sVxbvcNFCRC-lA_YXghyKdx8'
    list_folder = drive.ListFile({"q": "'{}' in parents and trashed=false".format(parent_id)}).GetList()
    folder_id=''
    
 
    folder_found = [ele['id'] for ele in list_folder if ele['title'] == folder_name]
    if len(folder_found)>0:
        folder_id = folder_found[0]
        
    else:

     
        file_metadata = {
          'title': folder_name,
          'mimeType': 'application/vnd.google-apps.folder'
        }
        file_metadata['parents'] = [{"kind": "drive#parentReference", "id": parent_id}]
        folder = drive.CreateFile(file_metadata)

        folder.Upload()
        folder_id = folder['id']
        
    return folder_id

def upload_xdelta(xdelta_name, folder_name):
    
    gauth = GoogleAuth()
    scope = ["https://www.googleapis.com/auth/drive"]
    gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name("../gsheet.json", scope)
    drive = GoogleDrive(gauth)
    
    #xdelta_name = r"G:\TalesHacking\PythonLib_Playground\Data\Tales-Of-Rebirth\Disc\New\Tales-Of-Rebirth_patch.xdelta"
    
    folder_id = get_folder(drive, folder_name)
    
    gfile = drive.CreateFile({'parents': [{'id': folder_id}]})
    
    
    file_name = os.path.basename(xdelta_name)
    gfile['title'] = file_name
    
    gfile.SetContentFile(xdelta_name)
    gfile.Upload() # Upload the file.
    
    
    file = get_file(drive, xdelta_name, folder_name)
    
    return file['webContentLink']