const mix = require("laravel-mix");

mix
  .js("src/js/app.js", "js")
  .js("src/js/script.js", "js")
  .js("src/js/libs/components.js", "js/libs")
  .js("src/js/libs/forms.js", "js/libs")
  .postCss("src/css/app.css", "css", [
    "@tailwindcss/postcss",
  ])
  .css("src/css/style.css", "css")
  .options({ processCssUrls: false })
  .webpackConfig({
    module: {
      rules: [
        {
          test: /\.js$/,
          enforce: "pre",
          use: ["source-map-loader"],
        },
      ],
    },
    devServer: {
      open: true,
    },
  })
  // .copyDirectory("src/html/", "assets")
  .copyDirectory("src/images", "assets/images")
  .copyDirectory("src/fonts", "assets/fonts")
  .setPublicPath("assets")
  .disableNotifications();

mix
    .js("src/js/pages/investor.js", "js/pages")


  .setPublicPath("assets")
  .disableNotifications();
