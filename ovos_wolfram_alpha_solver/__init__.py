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
from typing import Optional, List, Tuple

import requests
from ovos_config import Configuration
from ovos_plugin_manager.templates.agents import RetrievalEngine
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


class WolframAlphaSolver(RetrievalEngine):
    def __init__(self, config=None):
        super().__init__(config=config)
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

    def query(self, query: str, lang: Optional[str] = None, k: int = 3) -> List[Tuple[str, float]]:
        """
        Searches the knowledge base for relevant documents or data.

        Args:
            query: The search string.
            lang: BCP-47 language code.
            k: The maximum number of results to return.

        Returns:
            List of tuples (content, score) for the top k matches.
        """
        return [(self.get_spoken_answer(query, lang), 0.8)]

    # image api (simple)
    def get_image(self, query: str,
                  lang: Optional[str] = None,
                  units: Optional[str] = None):
        """
        return path/url to a single image to accompany spoken_answer
        """
        units = units or Configuration().get("system_unit", "metric")
        return self.api.get_image(query, units=units)

    # spoken answers api (spoken)
    def get_spoken_answer(self, query: str,
                          lang: Optional[str] = None,
                          units: Optional[str] = None):
        units = units or Configuration().get("system_unit", "metric")
        answer = self.api.spoken(query, units=units)
        bad_answers = ["no spoken result available",
                       "wolfram alpha did not understand your input"]
        if answer.lower().strip() in bad_answers:
            return None
        return answer


WOLFRAMALPHA_PERSONA = {
    "name": "Wolfram Alpha",
    "solvers": [
        "ovos-solver-plugin-wolfram-alpha",
        "ovos-solver-failure-plugin"
    ]
}

if __name__ == "__main__":
    s = WolframAlphaSolver()

    print(s.get_spoken_answer("venus", "en"))
    print(s.get_spoken_answer("elon musk", "en"))
    print(s.get_spoken_answer("mercury", "en"))
