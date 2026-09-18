import { Content } from '/lib/xp/content'
import { getSite, getContent } from '/lib/xp/portal'
import { localize } from '/lib/xp/i18n'

import { forceArray } from '/lib/app/util/collections'
import { getValue } from '/lib/app/extension/text-translation-manager'

export function getFieldValue(content: Content, field: string): unknown {
    if (!content) return undefined

    if (content.data && field in content.data) return content.data[field]
    else {
        const contentXData = (content.x && content.x[app.name]) || {}
        return contentXData.metadata && field in contentXData.metadata && contentXData.metadata[field]
    }
}

export function getParentPath(_path: string): string {
    return (_path?.replace(/\/$/, "").split("/").slice(0, -1).join("/")) || "/";
}

export function translate(key: string, params?: Record<string, string>): string {
    const site = getSite();
    const content = getContent();
    let translateValue = getValue(key, site, content);

    if (!translateValue) {
        const contentInherit = forceArray(content?.inherit);
        const isLocalize = contentInherit.indexOf("CONTENT") === -1;
        const mainLanguage = isLocalize ? content?.language || site?.language : site?.language;
        const language = mainLanguage ? mainLanguage.split("_")[0] : "no";
        translateValue = localize({ key: key, locale: language });
    }

    return applyParams(translateValue, params);
}

export function applyParams(value: string, params?: Record<string, string>): string {
    if (params) {
        const keys = Object.keys(params);
        for (let i = 0; i < keys.length; i++) {
            const regex = new RegExp(`<<${keys[i]}>>`, "g");
            value = value.replace(regex, params[keys[i]]);
        }
    }
    return value;
}

export function toStringOrDefault(strObj: unknown, defaultValue?: string): string | undefined {
    if (strObj === null || strObj === undefined) {
        return defaultValue;
    }
    const strObjAsRecord = strObj as Record<string, unknown>
    return typeof strObjAsRecord.toISOString === "function" ? (strObjAsRecord.toISOString as () => string)() : String(strObj);
}

export function generateRandomString(size: number = 10): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let randomString = '';
    for (let i = 0; i < size; i++) {
        const randomIndex = Math.floor(Math.random() * chars.length);
        randomString += chars.charAt(randomIndex);
    }
    return randomString;
}

export function unparseChars(body: string): string | undefined {
    if (!body) return;
    body = body.replace(new RegExp("ø", "g"), "o");
    body = body.replace(new RegExp("&amp;oslash;", "g"), "ø");
    body = body.replace(new RegExp("&oslash;", "g"), "ø");

    body = body.replace(new RegExp("Ø", "g"), "O");
    body = body.replace(new RegExp("&amp;Oslash;", "g"), "Ø");
    body = body.replace(new RegExp("&Oslash;", "g"), "Ø");

    body = body.replace(new RegExp("Æ", "g"), "AE");
    body = body.replace(new RegExp("&amp;Aelig;", "g"), "AE");
    body = body.replace(new RegExp("&Aelig;", "g"), "AE");

    body = body.replace(new RegExp("&AElig;", "g"), "AE");
    body = body.replace(new RegExp("&amp;AElig;", "g"), "AE");
    body = body.replace(new RegExp("&AElig;", "g"), "AE");

    body = body.replace(new RegExp("æ", "g"), "ae");
    body = body.replace(new RegExp("&amp;aelig;", "g"), "ae");
    body = body.replace(new RegExp("&aelig;", "g"), "ae");

    body = body.replace(new RegExp("å", "g"), "a");
    body = body.replace(new RegExp("&amp;aring;", "g"), "a");
    body = body.replace(new RegExp("&aring;", "g"), "a");

    body = body.replace(new RegExp("Å", "g"), "A");
    body = body.replace(new RegExp("&amp;Aring;", "g"), "Å");
    body = body.replace(new RegExp("&Aring;", "g"), "Å");

    body = body.replace(new RegExp("Ä", "g"), "A");
    body = body.replace(new RegExp("&amp;Auml;", "g"), "Ä");
    body = body.replace(new RegExp("&Auml;", "g"), "Ä");

    body = body.replace(new RegExp("ä", "g"), "a");
    body = body.replace(new RegExp("&amp;auml;", "g"), "ä");
    body = body.replace(new RegExp("&auml;", "g"), "ä");

    body = body.replace(new RegExp("Ð", "g"), "ETH");
    body = body.replace(new RegExp("&amp;ETH;", "g"), "Ð");
    body = body.replace(new RegExp("&ETH;", "g"), "Ð");

    body = body.replace(new RegExp("ð", "g"), "eth");
    body = body.replace(new RegExp("&amp;eth;", "g"), "ð");
    body = body.replace(new RegExp("&eth;", "g"), "ð");

    body = body.replace(new RegExp("Ö", "g"), "O");
    body = body.replace(new RegExp("&amp;Ouml;", "g"), "Ö");
    body = body.replace(new RegExp("&Ouml;", "g"), "Ö");

    body = body.replace(new RegExp("ö", "g"), "o");
    body = body.replace(new RegExp("&amp;ouml;", "g"), "ö");
    body = body.replace(new RegExp("&ouml;", "g"), "ö");

    body = body.replace(new RegExp("Þ", "g"), "Þ");
    body = body.replace(new RegExp("&amp;THORN;", "g"), "Þ");
    body = body.replace(new RegExp("&THORN;", "g"), "Þ");

    body = body.replace(new RegExp("á", "g"), "a");
    body = body.replace(new RegExp("Á", "g"), "A");

    body = body.replace(new RegExp("é", "g"), "e");
    body = body.replace(new RegExp("É", "g"), "E");

    body = body.replace(new RegExp("í;", "g"), "i");
    body = body.replace(new RegExp("Í", "g"), "I");

    body = body.replace(new RegExp("ó", "g"), "o");
    body = body.replace(new RegExp("Ó", "g"), "O");

    body = body.replace(new RegExp("ú", "g"), "u");
    body = body.replace(new RegExp("Ú", "g"), "U");

    body = body.replace(new RegExp("à", "g"), "a");
    body = body.replace(new RegExp("À", "g"), "A");

    body = body.replace(new RegExp("è", "g"), "e");
    body = body.replace(new RegExp("È", "g"), "E");

    body = body.replace(new RegExp("ì", "g"), "i");
    body = body.replace(new RegExp("Ì", "g"), "I");

    body = body.replace(new RegExp("ò", "g"), "o");
    body = body.replace(new RegExp("Ò", "g"), "O");

    body = body.replace(new RegExp("ù", "g"), "u");
    body = body.replace(new RegExp("Ù", "g"), "U");

    body = body.replace(new RegExp("â", "g"), "a");
    body = body.replace(new RegExp("Â", "g"), "A");

    body = body.replace(new RegExp("ê", "g"), "e");
    body = body.replace(new RegExp("Ê", "g"), "E");

    body = body.replace(new RegExp("î", "g"), "i");
    body = body.replace(new RegExp("Î", "g"), "I");

    body = body.replace(new RegExp("ô", "g"), "o");
    body = body.replace(new RegExp("Ô", "g"), "O");

    body = body.replace(new RegExp("û", "g"), "u");
    body = body.replace(new RegExp("Û", "g"), "U");

    return body;
}

export function removeTrailingSlash(str: string): string {
    if ((str || '').charAt((str || '').length - 1) === '/') {
        return str.slice(0, -1);
    }
    return str || '';
}

export function getPathLevel(siteUrl: string, fullPathUrl: string, currentPathName: string): number {
    const cleanSiteUrl = siteUrl.replace(/\/+$/, '');
    const cleanFullPathUrl = fullPathUrl.replace(/\/+$/, '');

    const pathPart = cleanFullPathUrl.replace(cleanSiteUrl, '');

    const segments = pathPart.split('/').filter(function (seg) {
        return seg.trim() !== '';
    });

    const lowerName = currentPathName.toLowerCase();

    for (let i = 0; i < segments.length; i++) {
        if (segments[i].toLowerCase() === lowerName) {
            return i + 1;
        }
    }

    return -1;
}

export function encodeBase64(input: string): string {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
    let result = ''
    let i = 0
    
    while (i < input.length) {
        const a = input.charCodeAt(i++)
        const b = i < input.length ? input.charCodeAt(i++) : 0
        const c = i < input.length ? input.charCodeAt(i++) : 0
        
        const bitmap = (a << 16) | (b << 8) | c
        
        result += chars.charAt((bitmap >> 18) & 63)
        result += chars.charAt((bitmap >> 12) & 63)
        result += i - 2 < input.length ? chars.charAt((bitmap >> 6) & 63) : '='
        result += i - 1 < input.length ? chars.charAt(bitmap & 63) : '='
    }
    
    return result
}

export function capitalizeFirstLetter(str: string): string {
    if (!str || typeof str !== 'string') return '';
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}
