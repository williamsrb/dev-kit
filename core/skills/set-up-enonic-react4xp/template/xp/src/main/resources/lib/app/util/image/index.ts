import { imageUrl as portalImageUrl, attachmentUrl } from '/lib/xp/portal'
import { get } from '/lib/xp/content'

interface ImageHandlerParams {
	sizes: number[]
	quality?: number
}

interface ImageDimensions {
	x: number
	y: number
}

interface ScaleTypes {
	x: string[]
	y: string[]
	xy: string[]
}

interface Placeholder {
	x: number | string
	y: string
	heightPercentage?: string
	src?: string
}

type ScaleParam = `block(${number},${number})` | `height(${number})` | `max(${number})` | `square(${number})` | `wide(${number},${number})` | `width(${number})` | 'full'

interface ImageContentData {
	_id: string
	type: string
	displayName: string
	data?: Record<string, unknown>
	x?: {
		media?: {
			imageInfo?: {
				imageWidth: number
				imageHeight: number
			}
		}
	}
}

interface ImageHandlerInstance {
	preScaledImageSizes: number[]
	defaultImageQuality: number
	createUrl: (imageBaseUrl: string, key: string, scale: string, filter: string, format: string, quality: number) => string
	createSrc: (imageBaseUrl: string, scaledWidth: number, image: ImageContentData, scale: string, filter: string, format: string, quality: number) => string
	createSrcSet: (imageBaseUrl: string, image: ImageContentData, scale: string, filter: string, format: string, quality: number) => string[]
}

interface ImageCreateParams {
	key: string
	scale?: string
	filter?: string
	format?: string
	quality?: number
	isResponsive?: boolean
	imageBaseUrl?: string
}

interface ImageResult {
	src: string
	srcSet?: string
	isResponsive: boolean
	title: string
	alt: string
	caption: string
	width?: number | string
	height?: string
	heightPercentage?: string
	placeholderSrc?: string
}

interface ExtractedScale {
	type: string
	values: string[]
}

function getScaleTypes(): ScaleTypes {
	return {
		x: ['width', 'square', 'max'],
		y: ['height'],
		xy: ['wide', 'block']
	}
}

function greatestCommonDivisor(a: number, b: number): number {
	return b ? greatestCommonDivisor(b, a % b) : Math.abs(a)
}

function getImageDimensions(image: ImageContentData): ImageDimensions {
	const imageInfo = image.x.media.imageInfo
	const imageDimensions: ImageDimensions = {
		x: imageInfo.imageWidth,
		y: imageInfo.imageHeight
	}
	return imageDimensions
}

function getImageAspectRatio(image: ImageContentData): number {
	const imageDimensions = getImageDimensions(image)
	return imageDimensions.x / imageDimensions.y
}

function getScaleParameters(scale: string): string[] {
	let res = scale.replace(/\)$/, '')
	res = res.split(/[(,]/) as unknown as string
	return res as unknown as string[]
}

function createScaleFilter(image: ImageContentData, scale: string, width: number): string {
	const scaleParams = getScaleParameters(scale)
	const scaleType = scaleParams[0].toLowerCase()
	const finalScaleFilterArray: number[] = []

	const scaleTypes = getScaleTypes()

	if (scaleTypes.x.indexOf(scaleType) >= 0) {
		finalScaleFilterArray.push(width)
	}

	if (scaleTypes.y.indexOf(scaleType) >= 0) {
		log.warning('Height scaling does not make sense for responsive images')
	}

	if (scaleTypes.xy.indexOf(scaleType) >= 0) {
		const scaleRatio = Number(scaleParams[1]) / Number(scaleParams[2])
		finalScaleFilterArray.push(width)
		finalScaleFilterArray.push(Math.round(width / scaleRatio))
	}

	if (scaleParams[3]) {
		finalScaleFilterArray.push(Number(scaleParams[3]))
	}

	if (scaleParams[4]) {
		finalScaleFilterArray.push(Number(scaleParams[4]))
	}

	return `${scaleType}(${finalScaleFilterArray.join()})`
}

function createScaledPlaceholder(image: ImageContentData, scale: string, width: number): Placeholder {
	const scaleParams = getScaleParameters(scale)
	const scaleType = scaleParams[0].toLowerCase()
	const placeholder: Placeholder = { x: 0, y: '0' }
	let scaleRatio = 1

	const scaleTypes = getScaleTypes()

	if (scaleTypes.xy.indexOf(scaleType) >= 0) {
		scaleRatio = Number(scaleParams[1]) / Number(scaleParams[2])
	} else if (scaleType === 'square') {
		scaleRatio = 1
	} else {
		scaleRatio = getImageAspectRatio(image)
	}

	const height = width / scaleRatio
	placeholder.x = width
	placeholder.y = String(Math.round(height))
	placeholder.heightPercentage = String((100 * height) / width)

	return placeholder
}

function createPlaceholder(image: ImageContentData, scaling: string): Placeholder {
	const scaleParams = getScaleParameters(scaling)
	const scaleType = scaleParams[0].toLowerCase()
	const scaleTypes = getScaleTypes()

	const scaleDimensions: ImageDimensions = { x: Number(scaleParams[1]), y: 0 }

	if (scaleTypes.xy.indexOf(scaleType) >= 0) {
		scaleDimensions.y = Number(scaleParams[2])
	} else {
		const y = Math.round(Number(scaleParams[1]) / getImageAspectRatio(image))
		scaleDimensions.y = y
	}

	const gcd = greatestCommonDivisor(scaleDimensions.x, scaleDimensions.y)

	const placeholder: Placeholder = {
		x: (scaleDimensions.x / gcd).toString(),
		y: (scaleDimensions.y / gcd).toString()
	}

	return placeholder
}

export function ImageHandler(this: ImageHandlerInstance, params: ImageHandlerParams): void {
	if (!params) throw new Error('Params must be provided')
	if (!params.sizes.length) throw new Error('At least one size should be provided')

	this.preScaledImageSizes = params.sizes || []
	this.defaultImageQuality = params.quality || 60
}

ImageHandler.prototype.createUrl = function createUrl(
	imageBaseUrl: string,
	key: string,
	scale: string,
	filter: string,
	format: string,
	quality: number
): string {
	function extractScale(): ExtractedScale | string {
		if (scale) {
			const splitValue = scale.split(/[()]/)
			const type = splitValue[0]
			const values = splitValue[1].split(',')

			return {
				type: type,
				values: values
			}
		}

		return ''
	}

	function extractParams(scaledQuality: number): string {
		let urlParams = ''

		if (filter) {
			urlParams = (urlParams ? '&' : '?') + `filter=${encodeURIComponent(filter.replace(filter, ''))}`
		}

		if (quality) {
			urlParams = (urlParams ? '&' : '?') + `quality=${scaledQuality}`
		}

		return urlParams
	}

	const scaledQuality = quality || this.defaultImageQuality

	if (imageBaseUrl) {
		const scaleReplace = extractScale() as ExtractedScale
		const imageName = imageBaseUrl.substr(imageBaseUrl.lastIndexOf('/'))

		let url = imageBaseUrl.replace('/block-99-99/', `${scaleReplace ? `/${scaleReplace.type}-${scaleReplace.values.join('-')}/` : `/`}`)

		if (format && (imageName.indexOf(`.${format}`) === -1)) {
			url = url + `.${format}`
		}

		url = url + extractParams(scaledQuality)

		return url
	} else {
		return portalImageUrl({
			id: key,
			scale: scale as ScaleParam,
			filter: filter,
			format: format,
			quality: scaledQuality
		})
	}
}

ImageHandler.prototype.createSrc = function createSrc(
	imageBaseUrl: string,
	scaledWidth: number,
	image: ImageContentData,
	scale: string,
	filter: string,
	format: string,
	quality: number
): string {
	const scalingFilter = createScaleFilter(image, scale, scaledWidth)
	const scaledQuality = quality || this.defaultImageQuality
	return this.createUrl(imageBaseUrl, image._id, scalingFilter, filter, format, scaledQuality)
}

ImageHandler.prototype.createSrcSet = function createSrcSet(
	imageBaseUrl: string,
	image: ImageContentData,
	scale: string,
	filter: string,
	format: string,
	quality: number
): string[] {
	const srcSet: string[] = []
	for (const element of this.preScaledImageSizes.entries()) {
		if (element[0] == 0) {
			const scaledWidth = element[1]
			const scaledQuality = quality || this.defaultImageQuality
			const scalingFilter = createScaleFilter(image, scale, scaledWidth)
			const scaledUrl = this.createUrl(
				imageBaseUrl,
				image._id,
				scalingFilter,
				filter,
				format,
				scaledQuality
			)

			srcSet.push(`${scaledUrl} ${scaledWidth}w`)
		} else {
			const scaledWidth = element[1]
			const index = element[0] + 1
			const scaledQuality = quality || this.defaultImageQuality
			const scalingFilter = createScaleFilter(image, scale, scaledWidth)
			const scaledUrl = this.createUrl(
				imageBaseUrl,
				image._id,
				scalingFilter,
				filter,
				format,
				scaledQuality
			)
			srcSet.push(`${scaledUrl} ${index}x`)
		}
	}
	return srcSet
}

export function getImageBaseUrl(params: { key: string }): string | undefined {
	if (!params || !params.key) return

	return portalImageUrl({ id: params.key, scale: 'block(99,99)' })
}

ImageHandler.prototype.create = function create(params: ImageCreateParams): ImageResult | undefined {
	if (!params || !params.key) return
	if (typeof params.isResponsive === 'undefined') params.isResponsive = true

	const image: Partial<ImageResult> = {}
	const result = get({ key: params.key })

	if (!result) return

	if (result.type !== 'media:image') image.src = attachmentUrl({ id: params.key })

	image.isResponsive = params.isResponsive

	if (result.type === 'media:image') {
		if (params.isResponsive) {
			image.srcSet = this.createSrcSet(params.imageBaseUrl, result, params.scale, params.filter, params.format, params.quality).join(', ')
			image.src = this.createSrc(params.imageBaseUrl, this.preScaledImageSizes[this.preScaledImageSizes.length - 1], result, params.scale, params.filter, params.format, params.quality)
			const placeHolder = createScaledPlaceholder(result, params.scale, this.preScaledImageSizes[this.preScaledImageSizes.length - 1])
			if (placeHolder && placeHolder.x && placeHolder.y) {
				image.width = placeHolder.x
				image.height = placeHolder.y
				image.heightPercentage = placeHolder.heightPercentage
				image.placeholderSrc = placeHolder.src
			}
		} else {
			image.src = this.createUrl(params.imageBaseUrl, params.key, params.scale, params.filter, params.format, params.quality)
		}
	}

	image.title = result.displayName || ''
	image.alt = (result.data && (result.data['altText'] as string)) || result.displayName || ''
	image.caption = (result.data && (result.data['caption'] as string)) || ''

	return image as ImageResult
}
