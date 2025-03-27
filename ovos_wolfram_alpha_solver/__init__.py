# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import tempfile
from os.path import join, isfile
from typing import Optional

import requests
from ovos_config import Configuration
from ovos_plugin_manager.templates.language import LanguageTranslator, LanguageDetector
from ovos_plugin_manager.templates.solvers import QuestionSolver
from ovos_utils.text_utils import rm_parentheses


class WolframAlphaApi:
    def __init__(self, key: str):
        self.key = key or "Y7R353-9HQAAL8KKA"

    @staticmethod
    def _get_lat_lon(**kwargs):
        lat = kwargs.get("latitude") or kwargs.get("lat")
        lon = kwargs.get("longitude") or kwargs.get("lon") or kwargs.get("lng")
        if not lat or not lon:
            cfg = Configuration().get("location", {}).get("coordinate", {})
            lat = cfg.get("latitude")
            lon = cfg.get("longitude")
        return lat, lon

    def spoken(self, query, units="metric", lat_lon=None, optional_params=None):
        optional_params = optional_params or {}
        if not lat_lon:
            lat_lon = self._get_lat_lon(**optional_params)
        params = {'i': query,
                  "geolocation": "{},{}".format(*lat_lon),
                  'units': units,
                  "appid": self.key,
                  **optional_params}
        url = 'https://api.wolframalpha.com/v1/spoken'
        return requests.get(url, params=params).text

    def simple(self, query, units="metric", lat_lon=None, optional_params=None):
        optional_params = optional_params or {}
        if not lat_lon:
            lat_lon = self._get_lat_lon(**optional_params)
        params = {'i': query,
                  "geolocation": "{},{}".format(*lat_lon),
                  'units': units,
                  "appid": self.key,
                  **optional_params}
        url = 'https://api.wolframalpha.com/v1/simple'
        return requests.get(url, params=params).text

    def full_results(self, query, units="metric", lat_lon=None, optional_params=None):
        """Wrapper for the WolframAlpha Full Results v2 API.
        https://products.wolframalpha.com/api/documentation/
        Pods of interest
        - Input interpretation - Wolfram's determination of what is being asked about.
        - Name - primary name of
        """
        optional_params = optional_params or {}
        if not lat_lon:
            lat_lon = self._get_lat_lon(**optional_params)
        params = {'input': query,
                  "units": units,
                  "mode": "Default",
                  "format": "image,plaintext",
                  "geolocation": "{},{}".format(*lat_lon),
                  "output": "json",
                  "appid": self.key,
                  **optional_params}
        url = 'https://api.wolframalpha.com/v2/query'
        data = requests.get(url, params=params)
        return data.json()

    def get_image(self, query: str, units: Optional[str] = None):
        """
        query assured to be in self.default_lang
        return path/url to a single image to acompany spoken_answer
        """
        units = units or Configuration().get("system_unit", "metric")
        url = 'http://api.wolframalpha.com/v1/simple'
        params = {"appid": self.key,
                  "i": query,
                  # "background": "F5F5F5",
                  "layout": "labelbar",
                  "units": units}
        path = join(tempfile.gettempdir(), query.replace(" ", "_") + ".gif")
        if not isfile(path):
            image = requests.get(url, params=params).content
            with open(path, "wb") as f:
                f.write(image)
        return path


class WolframAlphaSolver(QuestionSolver):
    def __init__(self, config=None,
                 translator: Optional[LanguageTranslator] = None,
                 detector: Optional[LanguageDetector] = None):
        super().__init__(config=config, priority=25,
                         internal_lang="en",
                         enable_tx=True, enable_cache=False,
                         translator=translator, detector=detector)
        self.api = WolframAlphaApi(key=self.config.get("appid") or "Y7R353-9HQAAL8KKA")

    @staticmethod
    def make_speakable(summary: str):
        # let's remove unwanted data from parantheses
        #  - many results have (human: XX unit) ref values, remove them
        if "(human: " in summary:
            splits = summary.split("(human: ")
            for idx, s in enumerate(splits):
                splits[idx] = ")".join(s.split(")")[1:])
            summary = " ".join(splits)

        # remove duplicated units in text
        # TODO probably there's a lot more to add here....
        replaces = {
            "cm (centimeters)": "centimeters",
            "cm³ (cubic centimeters)": "cubic centimeters",
            "cm² (square centimeters)": "square centimeters",
            "mm (millimeters)": "millimeters",
            "mm² (square millimeters)": "square millimeters",
            "mm³ (cubic millimeters)": "cubic millimeters",
            "kg (kilograms)": "kilograms",
            "kHz (kilohertz)": "kilohertz",
            "ns (nanoseconds)": "nanoseconds",
            "µs (microseconds)": "microseconds",
            "m/s (meters per second)": "meters per second",
            "km/s (kilometers per second)": "kilometers per second",
            "mi/s (miles per second)": "miles per second",
            "mph (miles per hour)": "miles per hour",
            "ª (degrees)": " degrees"
        }
        for k, v in replaces.items():
            summary = summary.replace(k, v)

        # replace units, only if they are individual words
        units = {
            "cm": "centimeters",
            "cm³": "cubic centimeters",
            "cm²": "square centimeters",
            "mm": "millimeters",
            "mm²": "square millimeters",
            "mm³": "cubic millimeters",
            "kg": "kilograms",
            "kHz": "kilohertz",
            "ns": "nanoseconds",
            "µs": "microseconds",
            "m/s": "meters per second",
            "km/s": "kilometers per second",
            "mi/s": "miles per second",
            "mph": "miles per hour"
        }
        words = [w if w not in units else units[w]
                 for w in summary.split(" ")]
        summary = " ".join(words)
        return rm_parentheses(summary)

    # data api
    def get_data(self, query: str,
                 lang: Optional[str] = None,
                 units: Optional[str] = None):
        """
       query assured to be in self.default_lang
       return a dict response
       """
        units = units or Configuration().get("system_unit", "metric")
        return self.api.full_results(query, units=units)

    # image api (simple)
    def get_image(self, query: str,
                  lang: Optional[str] = None,
                  units: Optional[str] = None):
        """
        query assured to be in self.default_lang
        return path/url to a single image to acompany spoken_answer
        """
        units = units or Configuration().get("system_unit", "metric")
        return self.api.get_image(query, units=units)

    # spoken answers api (spoken)
    def get_spoken_answer(self, query: str,
                          lang: Optional[str] = None,
                          units: Optional[str] = None):
        """
        query assured to be in self.default_lang
        return a single sentence text response
        """
        units = units or Configuration().get("system_unit", "metric")
        answer = self.api.spoken(query, units=units)
        bad_answers = ["no spoken result available",
                       "wolfram alpha did not understand your input"]
        if answer.lower().strip() in bad_answers:
            return None
        return answer

    def get_expanded_answer(self, query,
                            lang: Optional[str] = None,
                            units: Optional[str] = None):
        """
        query assured to be in self.default_lang
        return a list of ordered steps to expand the answer, eg, "tell me more"

        {
            "title": "optional",
            "summary": "speak this",
            "img": "optional/path/or/url
        }
        """
        data = self.get_data(query, lang, units)
        # these are returned in spoken answer or otherwise unwanted
        skip = ['Input interpretation', 'Interpretation',
                'Result', 'Value', 'Image']
        steps = []

        for pod in data['queryresult'].get('pods', []):
            title = pod["title"]
            if title in skip:
                continue

            for sub in pod["subpods"]:
                subpod = {"title": title}
                summary = sub["img"]["alt"]
                subtitle = sub.get("title") or sub["img"]["title"]
                if subtitle and subtitle != summary:
                    subpod["title"] = subtitle

                if summary == title:
                    # it's an image result
                    subpod["img"] = sub["img"]["src"]
                elif summary.startswith("(") and summary.endswith(")"):
                    continue
                else:
                    subpod["summary"] = summary
                steps.append(subpod)

        # do any extra processing here
        prev = ""
        for idx, step in enumerate(steps):
            # merge steps
            if step["title"] == prev:
                summary = steps[idx - 1]["summary"] + "\n" + step["summary"]
                steps[idx]["summary"] = summary
                steps[idx]["img"] = step.get("img") or steps[idx - 1].get("img")
                steps[idx - 1] = None
            elif step.get("summary") and step["title"]:
                # inject title in speech, eg we do not want wolfram to just read family names without context
                steps[idx]["summary"] = step["title"] + ".\n" + step["summary"]

            # normalize summary
            if step.get("summary"):
                steps[idx]["summary"] = self.make_speakable(steps[idx]["summary"])

            prev = step["title"]
        return [s for s in steps if s]


WOLFRAMALPHA_PERSONA = {
    "name": "Wolfram Alpha",
    "solvers": [
        "ovos-solver-plugin-wolfram-alpha",
        "ovos-solver-failure-plugin"
    ]
}

if __name__ == "__main__":
    s = WolframAlphaSolver()
    print(s.spoken_answer("quem é Elon Musk", lang="pt"))
    # ('who is Elon Musk', <CQSMatchLevel.GENERAL: 3>, 'The Musk family is a wealthy family of South African origin that is largely active in the United States and Canada.',
    # {'query': 'who is Elon Musk', 'image': None, 'title': 'Musk Family',
    # 'answer': 'The Musk family is a wealthy family of South African origin that is largely active in the United States and Canada.'})

    print(s.get_spoken_answer("venus", "en"))
    print(s.get_spoken_answer("elon musk", "en"))
    print(s.get_spoken_answer("mercury", "en"))
