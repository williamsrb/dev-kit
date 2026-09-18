import {PageComponent} from "@enonic-types/core";
import type {ComponentProcessor} from '@enonic-types/lib-react4xp/DataFetcher';

export const defaultPageProcessor: ComponentProcessor<'com.enonic.app.react4xp:Page'> = (props) => {
    const {regions} = props.component as PageComponent;

    return {
        regions
    };
};
