import {ComponentRegistry} from '@enonic/react-components';
import {DefaultPage} from './components/pages/default/default';

export const componentRegistry = new ComponentRegistry();

// Pages
componentRegistry.addPage('com.example.{PROJECT_SHORT_NAME}:default', {View: DefaultPage});
