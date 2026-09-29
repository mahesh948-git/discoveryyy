from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from CiscoInfoGrabber import CiscoInfoGrabber
import secrets

app = FastAPI()

security = HTTPBasic()

# Replace these with your actual username and password
USERNAME = "cisco"
PASSWORD = "Tfiber@1234"

def authenticate(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/")
async def get_ip(ip: str, username: str = Depends(authenticate)):
    if not ip:
        raise HTTPException(status_code=400, detail="IP address parameter missing")

    ip_address = ip.split(",")[0].strip()  # Extract the first IP if there are multiple
    grabber = CiscoInfoGrabber(ip_address)
    return JSONResponse(content=grabber.get_router_info())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
