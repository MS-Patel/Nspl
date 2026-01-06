const mix = require("laravel-mix");
const fs = require("fs");
const path = require("path");

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

// Automatically find and compile all files in src/js/pages
const pagesPath = 'src/js/pages';
if (fs.existsSync(pagesPath)) {
    const pageFiles = fs.readdirSync(pagesPath);
    pageFiles.forEach(file => {
        if (path.extname(file) === '.js') {
            mix.js(`${pagesPath}/${file}`, 'js/pages');
        }
    });
}
