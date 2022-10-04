import argparse
import sys

import cloudphoto_functions


def main():
    parser = argparse.ArgumentParser(description='Cloud photo archive')
    parser.add_argument('command')
    parser.add_argument('--album', default=None)
    parser.add_argument('--photo')
    parser.add_argument('--path', default='.')
    args = parser.parse_args()
    match args.command:
        case 'init':
            cloudphoto_functions.init()
        case 'upload':
            cloudphoto_functions.upload(args.album, args.path)
        case 'download':
            cloudphoto_functions.download(args.album, args.path)
        case 'list':
            cloudphoto_functions.photo_list(args.album)
        case 'delete':
            cloudphoto_functions.delete(args.album, args.photo)
        case 'mksite':
            cloudphoto_functions.make_site()
        case _:
            print('Unknown command', file=sys.stderr)
            exit(1)


if __name__ == '__main__':
    main()
