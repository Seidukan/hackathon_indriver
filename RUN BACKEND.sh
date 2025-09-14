python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app 
ngrok http 8000
#Install ngrok from website
#select the generated https link and use it in the webhook setup
#change the URI in App.js
