# BubbleIO RFP Leads Tracker

## Operating System:

- macOS | Linux | Windows

## Prerequisites
1. Install Python
2. Install Pycharm & Open the project in Pycharm
3. Install script requirements
   ```bash 
   pip install -r requirements.txt
    ```


## Add Environment Variables | Secrets

Copy `example.env.prod` as `.env.prod` and fill the Environment variables.

```bash
cp env.example .env
```

## Running the Scripts

1. Requests
    ```bash
   python3 app/requests_main.py
   ```
2. Bids
     ```bash
   python3 app/bids_main.py
   ```