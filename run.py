import uvicorn
import sys

if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    if getattr(sys, 'frozen', False):
        log_config["formatters"]["default"]["use_colors"] = False
        log_config["formatters"]["access"]["use_colors"] = False
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=21632, log_config=log_config)