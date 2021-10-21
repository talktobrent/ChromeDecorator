from browser import Base
import json
import base64
import os
import time
import tempfile


def screenshot(driver, path, name, options={}):
    """
    Sends screenshot command to browser

    https://stackoverflow.com/a/57507185
    https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-captureScreenshot

    @param driver: browser
    @type driver: selenium Chrome driver

    @param path: path to save to
    @type path: string

    @param name: school name
    @type name: string

    @param options: options for capturing screenshot
    @type options: dictionary
    """

    result = send_devtools(driver, "Page.captureScreenshot", options)
    with open(os.path.join(path, name + u'.png'), 'wb') as f:
        f.write(base64.b64decode(result['data']))
        f.close()

    return os.path.join(path, name + '.png')

def save_as_pdf(driver, path, name, options={}):
    """
    Tells browser to save as pdf

    https://stackoverflow.com/a/57507185
    https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF

    @param driver: browser
    @type driver: selenium Chrome driver

    @param path: path to save pdf to
    @type path: string

    @param options: options for printing
    @type options: dictionary
    """

    result = send_devtools(driver, "Page.printToPDF", options)
    with open(os.path.join(path, name), 'wb') as f:
        f.write(base64.b64decode(result['data']))
        f.close()

    return os.path.join(path, name)

def send_devtools(driver, cmd, params):
    """
    Communicate with ChromeBrowser

    https://stackoverflow.com/a/57507185

    @param driver: browser
    @type driver: selenium driver

    @param cmd: command to send to browser
    @type cmd: string

    @param params: parameters of command
    @type params: dictionary

    @return: response
    @rtype: dictionary
    """
    resource = "/session/{}/chromium/send_command_and_get_result".format(driver.session_id)
    url = driver.command_executor._url + resource
    body = json.dumps({'cmd': cmd, 'params': params})
    response = driver.command_executor._request('POST', url, body)
    if response.get('status', None):
        raise Exception(response.get('value'))
    return response.get('value')


class ChromePDF(Chrome):
    """
    Decorator to get and/or print webpages and/or take screenshots before and after a function is applied on the
    webpage via selenium with ChromeDriver
    """

    @property
    def page(self):
        page = "pdfchrome-" + str(self._page)
        self._page += 1
        return page


    def __init__(self, url="", wait=3, location=tempfile.gettempdir(), chrome_args={}):

        super().__init__(**chrome_args)
        self._page = 0
        self.wait = wait
        self.location = location
        if url:
            self.get(url)


    def screenshot(self, height=0, width=0, location="", devtools=[]):
        """
        Sets up browser to take optimal screenshot
        https://chromedevtools.github.io/devtools-protocol/tot/Emulation/

        @param path: path to save screenshot
        @type path: string

        @param name: name of course
        @type name: string
        """

        if height and width:
            send_devtools(self.driver, "Emulation.setDeviceMetricsOverride",
                          {"width": width, "height": height, "deviceScaleFactor": 0, "mobile": False})

        for devtool in devtools:
            send_devtools(self.driver, devtool[0], devtool[1])

        send_devtools(self.driver, "Emulation.setScrollbarsHidden", {"hidden": True})
        output = screenshot(self.driver, location or self.location, self.page, {})
        send_devtools(self.driver, "Emulation.clearDeviceMetricsOverride", {})
        return output

    def pdf(self, height=0, width=0, page_range="", options={}, devtools=[], location=""):
        """
        Filters html and requests PDF from browser

        https://chromedevtools.github.io/devtools-protocol/tot/Emulation/#method-setEmulatedMedia
        https://chromedevtools.github.io/devtools-protocol/tot/Page/#method-printToPDF
        https://developer.mozilla.org/en-US/docs/Web/CSS/-webkit-print-color-adjust

        @return: file path of mapped pdf in tempdir
        @rtype: string
        """

        for devtool in devtools:
            send_devtools(self.driver, devtool[0], devtool[1])

        if height:
            options['paperHeight'] = height
        if width:
            options['paperWidth'] = width
        if page_range:
            options['pageRanges'] = page_range

        return save_as_pdf(self.driver, location or self.location, self.page, options)
