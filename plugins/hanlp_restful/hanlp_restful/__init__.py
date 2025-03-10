# -*- coding:utf-8 -*-
# Author: hankcs
# Date: 2020-11-29 17:48
import json
from typing import Union, List, Optional, Dict, Any, Tuple
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from hanlp_common.document import Document

try:
    # noinspection PyUnresolvedReferences
    import requests


    def _post(url, form: Dict[str, Any], headers: Dict[str, Any], timeout=5) -> str:
        response = requests.post(url, json=form, headers=headers, timeout=timeout)
        if response.status_code != 200:
            raise HTTPError(url, response.status_code, response.text, response.headers, None)
        return response.text
except ImportError:
    def _post(url, form: Dict[str, Any], headers: Dict[str, Any], timeout=5) -> str:
        request = Request(url, json.dumps(form).encode())
        for k, v in headers.items():
            request.add_header(k, v)
        return urlopen(request, timeout=timeout).read().decode()


class HanLPClient(object):

    def __init__(self, url: str, auth: str = None, language=None, timeout=5) -> None:
        """

        Args:
            url (str): An API endpoint to a service provider.
            auth (str): An auth key licenced from a service provider.
            language (str): The default language for each :func:`~hanlp_restful.HanLPClient.parse` call.
                Contact the service provider for the list of languages supported.
                Conventionally, ``zh`` is used for Chinese and ``mul`` for multilingual.
                Leave ``None`` to use the default language on server.
            timeout (int): Maximum waiting time in seconds for a request.
        """
        super().__init__()
        self._language = language
        self._timeout = timeout
        self._url = url
        if auth is None:
            import os
            auth = os.getenv('HANLP_AUTH', None)
        self._auth = auth

    def parse(self,
              text: Union[str, List[str]] = None,
              tokens: List[List[str]] = None,
              tasks: Optional[Union[str, List[str]]] = None,
              skip_tasks: Optional[Union[str, List[str]]] = None,
              language: str = None,
              ) -> Document:
        """
        Parse a piece of text.

        Args:
            text: A paragraph (str), or a list of sentences (List[str]).
            tokens: A list of sentences where each sentence is a list of tokens.
            tasks: The tasks to predict.
            skip_tasks: The tasks to skip.
            language: The language of input text or tokens. ``None`` to use the default language on server.

        Returns:
            A :class:`~hanlp_common.document.Document`.

        Raises:
            HTTPError: Any errors happening on the Internet side or the server side. Refer to the ``code`` and ``msg``
                of the exception for more details. A list of common errors :

        - ``400 Bad Request`` indicates that the server cannot process the request due to a client
          fault (e.g., text too long, language unsupported).
        - ``401 Unauthorized`` indicates that the request lacks **valid** ``auth`` credentials for the API.
        - ``422 Unprocessable Entity`` indicates that the content type of the request entity is not in
          proper json format.
        - ``429 Too Many Requests`` indicates the user has sent too many requests in a given
          amount of time ("rate limiting").

        """
        assert text or tokens, 'At least one of text or tokens has to be specified.'
        response = self._send_post_json(self._url + '/parse', {
            'text': text,
            'tokens': tokens,
            'tasks': tasks,
            'skip_tasks': skip_tasks,
            'language': language or self._language
        })
        return Document(response)

    def __call__(self,
                 text: Union[str, List[str]] = None,
                 tokens: List[List[str]] = None,
                 tasks: Optional[Union[str, List[str]]] = None,
                 skip_tasks: Optional[Union[str, List[str]]] = None,
                 language: str = None,
                 ) -> Document:
        """
        A shortcut of :meth:`~hanlp_restful.HanLPClient.parse`.
        """
        return self.parse(text, tokens, tasks, skip_tasks)

    def about(self) -> Dict[str, Any]:
        """Get the information about server and your client.

        Returns:
            A dict containing your rate limit and server version etc.

        """
        info = self._send_get_json(self._url + '/about', {})
        return Document(info)

    def _send_post(self, url, form: Dict[str, Any]):
        request = Request(url, json.dumps(form).encode())
        self._add_headers(request)
        return self._fire_request(request)

    def _fire_request(self, request):
        return urlopen(request, timeout=self._timeout).read().decode()

    def _send_post_json(self, url, form: Dict[str, Any]):
        headers = dict()
        if self._auth:
            headers['Authorization'] = f'Basic {self._auth}'
        return json.loads(_post(url, form, headers, self._timeout))

    def _send_get(self, url, form: Dict[str, Any]):
        request = Request(url + '?' + urlencode(form))
        self._add_headers(request)
        return self._fire_request(request)

    def _add_headers(self, request):
        if self._auth:
            request.add_header('Authorization', f'Basic {self._auth}')

    def _send_get_json(self, url, form: Dict[str, Any]):
        return json.loads(self._send_get(url, form))

    def text_style_transfer(self, text: Union[str, List[str]], target_style: str, language: str = None) \
            -> Union[str, List[str]]:
        """ Text style transfer aims to change the style of the input text to the target style while preserving its
        content.

        Args:
            text: Source text.
            target_style: Target style.
            language: The language of input text. ``None`` to use the default language.

        Examples::

            HanLP.text_style_transfer(['国家对中石油抱有很大的期望.', '要用创新去推动高质量的发展。'],
                                      target_style='gov_doc')
            # Output: ['国家对中石油寄予厚望。', '要以创新驱动高质量发展。']

        Returns:
            Text or a list of text of the target style.

        """
        response = self._send_post_json(self._url + '/text_style_transfer',
                                        {'text': text, 'target_style': target_style,
                                         'language': language or self._language})
        return response

    def semantic_textual_similarity(self, text: Union[Tuple[str, str], List[Tuple[str, str]]], language: str = None) \
            -> Union[float, List[float]]:
        """ Semantic textual similarity deals with determining how similar two pieces of texts are.

        Args:
            text: A pair or pairs of text.
            language: The language of input text. ``None`` to use the default language.

        Examples::

            HanLP.semantic_textual_similarity([
                ('看图猜一电影名', '看图猜电影'),
                ('无线路由器怎么无线上网', '无线上网卡和无线路由器怎么用'),
                ('北京到上海的动车票', '上海到北京的动车票'),
            ])
            # Output: [0.9764469861984253, 0.0, 0.003458738327026367]

        Returns:
            Similarities.

        """
        response = self._send_post_json(self._url + '/semantic_textual_similarity',
                                        {'text': text, 'language': language or self._language})
        return response
