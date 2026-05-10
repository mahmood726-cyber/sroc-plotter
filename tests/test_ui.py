from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


ROOT = Path(__file__).resolve().parents[1]


def _available_port(preferred=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            probe.bind(("127.0.0.1", 0))
            return probe.getsockname()[1]


@pytest.fixture(scope="module")
def server():
    port = _available_port()
    process = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            raise RuntimeError(f"HTTP server failed to start: {stderr}")
        try:
            urllib.request.urlopen(base_url, timeout=0.5).close()
            break
        except OSError:
            time.sleep(0.1)
    else:
        process.terminate()
        stderr = process.stderr.read() if process.stderr else ""
        raise RuntimeError(f"HTTP server did not become ready: {stderr}")
    try:
        yield base_url
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.fixture()
def driver(server):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    browser = webdriver.Chrome(options=options)
    try:
        yield browser
    finally:
        browser.quit()


def test_redirect_index_points_to_app(driver, server):
    driver.get(f"{server}/index.html")
    WebDriverWait(driver, 10).until(lambda d: "sroc-plotter.html" in d.current_url)

    assert driver.title.startswith("SROCPlotter")
    assert driver.find_element(By.CSS_SELECTOR, ".app-header h1").text.startswith("SROCPlotter")


def test_app_shell_loads(driver, server):
    driver.get(f"{server}/sroc-plotter.html")
    WebDriverWait(driver, 10).until(lambda d: d.find_element(By.CSS_SELECTOR, ".app-header h1").text.strip() != "")

    assert "SROCPlotter" in driver.title
    assert len(driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')) >= 4
    driver.find_element(By.ID, "tab-plot").click()
    WebDriverWait(driver, 10).until(lambda d: "active" in d.find_element(By.ID, "panel-plot").get_attribute("class"))
    assert driver.find_element(By.ID, "srocCanvas").is_displayed()
    assert driver.find_element(By.ID, "darkToggle").is_displayed()


def test_e156_page_loads(driver, server):
    driver.get(f"{server}/e156-submission/index.html")
    WebDriverWait(driver, 10).until(lambda d: d.find_element(By.ID, "title").text.strip() != "")

    assert driver.find_element(By.ID, "title").text == "Untitled E156"
    assert len(driver.find_elements(By.CSS_SELECTOR, "a")) >= 3
