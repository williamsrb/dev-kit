import { getAttachmentStream, get } from '/lib/xp/content'
import { readText } from '/lib/xp/io'

export function getMediaStreamText(id: string): string {
    const content = id && get({ key: id })

    if (!content) return ''

    const contentData = content.data as { media?: { attachment?: string } }
    const stream = contentData?.media?.attachment && getAttachmentStream({
        key: id,
        name: contentData.media.attachment
    })

    return readText(stream) || ''
}
