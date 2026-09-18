import {DataFetcher} from '/lib/enonic/react4xp';
import {defaultPageProcessor} from './components/pages/default/processor';

export const dataFetcher = new DataFetcher();

// Pages
dataFetcher.addPage(`${app.name}:default`, {processor: defaultPageProcessor});
