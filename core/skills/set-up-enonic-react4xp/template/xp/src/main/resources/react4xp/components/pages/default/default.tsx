import {Regions, type ComponentProps, type PageData} from '@enonic/react-components';
import Header from '/react4xp/components/prototype/Header';
import Footer from '/react4xp/components/prototype/Footer';

export const DefaultPage = ({data, common, meta, component}: ComponentProps<PageData>) => {

    return (
        <>
            <Header />
            <div>
                <Regions common={common} meta={meta} component={component}/>
            </div>
            <Footer />
        </>
    );
};
