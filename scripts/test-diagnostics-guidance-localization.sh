#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VIEW="${VIEW:-${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt}"
fail(){ echo "FAIL: $*" >&2; exit 1; }
EN_FIRST='Enter a domain that is currently blocked by your ISP and click “Run.” Multiple DPI bypass strategies will be tested over the next 1–3 minutes, after which the strategies that successfully provide access to the site will be reported.'
EN_SECOND='Review the results and add the required profile to the strategy currently in use on the “Settings” page.'
RU_FIRST='Введите домен, который в настоящее время блокируется вашим интернет-провайдером, и нажмите «Запустить». В течение 1–3 минут будут произведены множественные проверки стратегий обхода DPI, после чего будет сообщено, какие из них позволяют успешно открыть сайт.'
RU_SECOND='Изучите результат и добавьте необходимый профиль в используемую стратегию на странице «Настройки».'

grep -Fq "document.documentElement.lang || ''" "${VIEW}" || fail 'OPNsense language detection is missing'
grep -Fq 'var strategyLabGuidance = isRussian' "${VIEW}" || fail 'localized Strategy Lab guidance selection is missing'
grep -Fq '.text(paragraph)' "${VIEW}" || fail 'guidance paragraphs are not rendered safely'
grep -Fq '.appendTo(guidance)' "${VIEW}" || fail 'guidance paragraphs are not attached'
grep -Fq "${EN_FIRST}" "${VIEW}" || fail 'English first paragraph is missing'
grep -Fq "${EN_SECOND}" "${VIEW}" || fail 'English second paragraph is missing'
grep -Fq "${RU_FIRST}" "${VIEW}" || fail 'Russian first paragraph is missing'
grep -Fq "${RU_SECOND}" "${VIEW}" || fail 'Russian second paragraph is missing'
echo 'PASS: Strategy Lab guidance follows the selected OPNsense language'
