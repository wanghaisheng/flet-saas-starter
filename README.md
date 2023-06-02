
##  A boilerplate for building Software-as-Service (SAAS) 

Deploy Flet app as a web app and view it in a browser. Package it as a standalone desktop app for Windows, macOS and Linux. Install it on mobile as PWA or view via Flet app for iOS and Android.

if you are a python guy and looking for a saas solution ,take a look at this

**Flet enables developers to easily build realtime web, mobile and desktop apps in Python. No frontend experience required.**

<br/>
<p align="center">

  <a href="https://github.com/wanghaisheng/flet-saas-starter" >
    <img src="https://raw.githubusercontent.com/wanghaisheng/flet-saas-starter/main/assets/screenshot-homepage.png" alt="Logo"  width="49%">
  </a>
   <a href="https://github.com/wanghaisheng/flet-saas-starter">
    <img src="https://raw.githubusercontent.com/wanghaisheng/flet-saas-starter/main/assets/screenshot-login.png" alt="Logo" width="49%">
  </a>

  <h3 align="center">✨ Free Pure python Flet based multi-platfform desktop APP  template for SaaS startups ✨</h3>

  <p align="center">
    Everything you need to build a great multi-platfform desktop APP  for your idea.
    <br/>
    <br/>
    <a href="">View Demo</a>
    .
    <a href="https://github.com/wanghaisheng/flet-saas-starter/issues">Report Bug</a>
    .
    <a href="https://github.com/wanghaisheng/flet-saas-starter/issues">Request Feature</a>
  </p>
</p>


## Table Of Contents

- [Features](#-features)
- [Getting Started](#-getting-started)  
- [One click deploy](#one-click-deploy)  
- [Built With](#-built-with)
- [Contributing](#-contributing)
  - [Creating A Pull Request](#creating-a-pull-request)
- [Acknowledgements](#-acknowledgements)
- [Contributors](#-contributors)
- [License](#-license)

## Features

- [x] User account sign up, sign in, password reset, all through asynchronous email confirmation.
- [ ] Form generation.
- [ ] Error handling.
- [ ] HTML macros and layout file.
- [ ] "Functional" file structure.
- [ ] Python 3.x compliant.
- [ ] Asynchronous AJAX calls.
- [ ] Administration panel.
- [ ] Logging.
- [ ] Stripe subscriptions. (WIP)
- [ ] RESTful API for payments.
- [ ] Simple RESTful API to communicate with your app.



## 🤓 Getting Started

- Click `Use the template` or [this link](https://github.com/wanghaisheng/flet-saas-starter/generate)

```
# run dep install
$ pip install -r requirments.txt

# run the main
python main.py


```

> Hint: 



## 🚀 One click package to app

### windows  ubuntu macos

AppVeyor CI pipeline to build Flet app desktop package

github action CI pipeline to build Flet app desktop package



### iphone 

https://github.com/SKbarbon/fpyo2ipa



```
1- Create a flet dist folder from your main script.

its recomended to make the dist from a flet v0.6.1 or v0.6.2, because this is the version the package have been tested with.
flet publish main.py
2- create a python virtual environment.

python3 -m venv venv

3- activate venv 

source  /Users/wenke/github/flet-tiktoka-studio/venv/bin/activate

install this package.

pip install fpyo2ipa --upgrade
4- use this build tool.

python3 -m fpyo2ipa.build
```



check the app

All work done!
Your app is in the `pyo2ipadist/build/pyo2ipadist/iOS/xcode`!
To run a simulator, use:
$ cd pyo2ipadist
$ briefcase run iOS



    raise ImportError(
ImportError: urllib3 v2.0 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with LibreSSL 2.8.3. See: https://github.com/urllib3/urllib3/issues/2168



(venv) (base) wenke@wenkedeMac-mini pyo2ipadist % pip install 'urllib3<2.0'

Looking in indexes: https://pypi.tuna.tsinghua.edu.cn/simple
Collecting urllib3<2.0
  Using cached https://pypi.tuna.tsinghua.edu.cn/packages/7b/f5/890a0baca17a61c1f92f72b81d3c31523c99bec609e60c292ea55b387ae8/urllib3-1.26.15-py2.py3-none-any.whl (140 kB)
Installing collected packages: urllib3
Successfully installed urllib3-1.26.15
(venv) (base) wenke@wenkedeMac-mini pyo2ipadist % briefcase run iOS  




can simulate and can start app but app got blank 




### android 

#### Be sure that Android Studio is installed and setuped. 

https://github.com/SKbarbon/fpyo2apk


1- Publish your flet script into flet-pyodide dist. Use this command for that:

flet publish main.py
2- Create a python virtual environment (highly recommended):

python3 -m venv venv

3- Install fpyo2apk package:

pip install fpyo2apk --upgrade

4- Start building your Android App project.

Make sure that your dist folder is in the current cmd's folder, and make sure that you are done with Android Studio setup.
python3 -m fpyo2apk.build


$ cd fpyo2apkdist
$ briefcase create Android
$ briefcase build Android
$ briefcase run Android




## 🧰 Built With

- [Flet](https://github.com/flet-dev/flet)

https://github.com/ndonkoHenri/Python-Desktop-Notifications/tree/master



## 🤲🏻 Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

- If you have suggestions for adding or removing projects, feel free to [open an issue](https://github.com/wanghaisheng/flet-saas-starter/issues/new) to discuss it, or directly create a pull request after you edit the _README.md_ file with necessary changes.
- Create individual PR for each suggestion.

### Creating A Pull Request

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 😎 Acknowledgements

Big thanks to authors of these libraries:

- https://github.com/AlloryDante/Matrix-Rewards-Bot ——a dorable desktop app make me believe flet  works
- https://github.com/nbilbo/flet-alchemy- inspired me to build saas based on flet

## ✨ Contributors

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://nbilbo.github.io/"><img src="https://avatars.githubusercontent.com/u/56805899?v=4?s=64" width="64px;" alt=""/><br /><sub><b>Felipe Morais</b></sub></a><br /><a href="https://github.com/wanghaisheng/flet-saas-starter/commits?author=nbilbo" title="Code">💻</a></td>
    <td align="center"><a href="https://github.com/wanghaisheng"><img src="https://avatars.githubusercontent.com/u/2363295?v=4?s=64" width="64px;" alt=""/><br /><sub><b>wanghaisheng</b></sub></a><br /><a href="https://github.com/wanghaisheng/flet-saas-starter/commits?author=wanghaisheng" title="Code">💻</a></td>

  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!

## 📝 License

Distributed under the MIT License. See [LICENSE](https://github.com/wanghaisheng/flet-saas-starter/blob/main/LICENSE.md) for more information.
