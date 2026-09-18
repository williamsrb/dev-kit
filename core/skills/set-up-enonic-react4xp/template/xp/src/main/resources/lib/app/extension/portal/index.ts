import type { Content } from '@enonic-types/core';

import { exists, get } from '/lib/xp/content';
import { pageUrl, imageUrl, processHtml, attachmentUrl } from '/lib/xp/portal';

import { toStringOrDefault } from '/lib/app/util/strings';

interface ImageUrlResult {
	link: string
	alt: string
	title: string
	caption: string
}

interface LinkResult {
	href: string | null
	target: string
	rel?: string
	noLink?: boolean
}

type ScaleParam = `block(${number},${number})` | `height(${number})` | `max(${number})` | `square(${number})` | `wide(${number},${number})` | `width(${number})` | 'full'

export function getLink(internal: string, external?: string, openInNewTab?: boolean, content?: Content): LinkResult {
    if (internal) {
		if (content?.type?.indexOf('media:') === 0) {
			return {
				href: attachmentUrl({ id: content?._id, type: 'absolute' }),
				target: '_blank'
			}
		}

        return {
            href: myPageUrl(internal),
            target: openInNewTab ? '_blank' : '_self'
        }
    } else if (external) {
        return {
            href: external,
            target: '_blank',
            rel: 'noopener'
        }
    } else {
        return {
            href: null,
            target: '',
            noLink: true
        }
    }
}

export function myPageUrl(nodeID: string, params?: Record<string, string>): string | null {
    if (nodeID) {
        if (exists({ key: nodeID })) {
            return nodeID && pageUrl({
                id: nodeID,
                params: params,
                type: 'absolute'
            })
        }
    }
    return null
}

export function myImageUrl(imageId: string, scale: ScaleParam, format?: string, quality?: string): ImageUrlResult | null {
	if (imageId) {
		const imgObj = get({ key: imageId })
		if (!imgObj) {
			return null
		}
		const imgOpts: {
			id: string
			scale: ScaleParam
			type: 'server' | 'absolute'
			format?: string
			quality?: number
		} = {
			id: imageId,
			scale: (scale || 'width(720)') as ScaleParam,
			type: 'absolute'
		}

		if (format || quality) {
			if (imgObj.type !== 'media:vector' && format) {
				imgOpts.format = format
			}
			if (imgObj.type !== 'media:vector' && quality) {
				imgOpts.quality = Number(quality)
			}
		}

		const link = imageUrl(imgOpts)

		if (typeof link === 'string' && link.indexOf('error/404') === -1 && link.indexOf('error/500') === -1) {
			return {
				link,
				alt: imgObj.data?.altText as string || imgObj.displayName || '',
				title: imgObj.displayName || '',
				caption: imgObj.data?.caption as string || ''
			}
		} else {
			return null
		}
	} else {
		return null
	}
}

export function processHTMLField(HTMLAreaField?: string): string {
	if (HTMLAreaField) {
		HTMLAreaField = trimHTMLString(HTMLAreaField)
		HTMLAreaField = processHTMLTables(HTMLAreaField)
	}

	const processedText = HTMLAreaField && processHtml({
		value: HTMLAreaField
	})
	return toStringOrDefault(processedText, null) || ''
}

export function trimHTMLString(htmlString: string): string | undefined {
	if (htmlString && (typeof htmlString === 'string')) {
		htmlString = htmlString.replace(/^ *<p>(&nbsp;| )+/g, '<p>').replace(/(&nbsp;| )*<\/p>/g, '</p>')
		const htmlWithoutEmptyParagraphs = htmlString.replace(/<p><\/p>(\n)*/g, '')
		htmlString = htmlWithoutEmptyParagraphs === '' ? htmlWithoutEmptyParagraphs : htmlString.replace(/<p><\/p>(\n)*/g, '<br>')
	}
	return toStringOrDefault(htmlString)
}

export function processHTMLTables(htmlString: string): string | undefined {
	if (htmlString && (typeof htmlString === 'string')) {
		return htmlString
			.replace(/(width:)[\d]+(px)/g, '')
			.replace(/(height:)[\d]+(px)/g, '')
			.replace(/(width=)"[\d]+(%|px)?"/g, '')
			.replace(/(height=)"[\d]+(%|px)?"/g, '')
	}

	return toStringOrDefault(htmlString)
}

export function processTextArea(textArea: string = ''): string {
	return (textArea && textArea.replace(/\n/g, '<br>')) || ''
}

export function myAssetURL(assetPath: string, site: Content): string {
	let baseUrl = pageUrl({ path: `/${site._name}`, type: 'absolute' })

	baseUrl = (baseUrl.indexOf('/admin/site') === -1) ? baseUrl : baseUrl.substring(0, baseUrl.indexOf('/admin/site'))
	baseUrl = (baseUrl.lastIndexOf('/') === (baseUrl.length - 1)) ? baseUrl : `${baseUrl}/`

	return `${baseUrl}_/service/${app.name}/get-assets-url/${assetPath || ''}`
}

export function myAttachmentURL(attachmentId: string): string | null {
	if (!attachmentId) return null
	return attachmentUrl({
		id: attachmentId,
		type: 'absolute'
	})
}
