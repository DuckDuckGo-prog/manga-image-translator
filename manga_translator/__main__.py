import os
import asyncio
import logging
from argparse import Namespace

from manga_translator.share import MangaShare
from .manga_translator import (
    MangaTranslator,
    MangaTranslatorWeb,
    MangaTranslatorWS,
    MangaTranslatorAPI,
    set_main_logger,
)
from .args import parser
from .utils import (
    BASE_PATH,
    init_logging,
    get_logger,
    set_log_level,
    natural_sort,
)

# TODO: Dynamic imports to reduce ram usage in web(-server) mode. Will require dealing with args.py imports.

async def dispatch(args: Namespace):
    args_dict = vars(args)

    logger.info(f'Running in {args.mode} mode')

    if args.mode in ('demo', 'batch'):
        if not args.input:
            raise Exception('No input image was supplied. Use -i <image_path>')
        translator = MangaTranslator(args_dict)

        # Load pre-translation and post-translation dictionaries
        pre_dict = translator.load_dictionary(args.pre_dict)  
        post_dict = translator.load_dictionary(args.post_dict)  

        if args.mode == 'demo':
            if len(args.input) != 1 or not os.path.isfile(args.input[0]):
                raise FileNotFoundError(f'Invalid single image file path for demo mode: "{" ".join(args.input)}". Use `-m batch`.')
            dest = os.path.join(BASE_PATH, 'result/final.png')
            args.overwrite = True # Do overwrite result/final.png file

            # Apply pre-translation dictionaries
            await translator.translate_path(args.input[0], dest, args_dict)
            for textline in translator.textlines:
                textline.text = translator.apply_dictionary(textline.text, pre_dict)  
                logger.info(f'Pre-translation dictionary applied: {textline.text}')

            # Apply post-translation dictionaries
            for textline in translator.textlines:
                textline.translation = translator.apply_dictionary(textline.translation, post_dict)  
                logger.info(f'Post-translation dictionary applied: {textline.translation}')

        else: # batch
            dest = args.dest
            for path in natural_sort(args.input):
                try :
                    # Apply pre-translation dictionaries
                    await translator.translate_path(path, dest, args_dict)
                    for textline in translator.textlines:
                        textline.text = translator.apply_dictionary(textline.text, pre_dict) 
                        logger.info(f'Pre-translation dictionary applied: {textline.text}')

                    # Apply post-translation dictionaries
                    for textline in translator.textlines:
                        textline.translation = translator.apply_dictionary(textline.translation, post_dict)  
                        logger.info(f'Post-translation dictionary applied: {textline.translation}')
                except Exception :
                    pass

    elif args.mode == 'web':
        from .server.web_main import dispatch
        await dispatch(args.host, args.port, translation_params=args_dict)

    elif args.mode == 'web_client':
        translator = MangaTranslatorWeb(args_dict)
        await translator.listen(args_dict)

    elif args.mode == 'ws':
        translator = MangaTranslatorWS(args_dict)
        await translator.listen(args_dict)

    elif args.mode == 'api':
        translator = MangaTranslatorAPI(args_dict)
        await translator.listen(args_dict)
    elif args.mode == 'shared':
        translator = MangaShare(args_dict)
        await translator.listen(args_dict)



if __name__ == '__main__':
    args = None
    init_logging()
    try:
        args = parser.parse_args()
        set_log_level(level=logging.DEBUG if args.verbose else logging.INFO)
        logger = get_logger(args.mode)
        set_main_logger(logger)
        if args.mode != 'web':
            logger.debug(args)

        asyncio.run(dispatch(args))
    except KeyboardInterrupt:
        if not args or args.mode != 'web':
            print()
    except Exception as e:
        logger.error(f'{e.__class__.__name__}: {e}',
                     exc_info=e if args and args.verbose else None)
