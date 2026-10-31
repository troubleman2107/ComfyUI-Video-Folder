from .video_folder import LoadVideosFromFolder

NODE_CLASS_MAPPINGS = {'TM_LoadVideosFromFolder': LoadVideosFromFolder}
NODE_DISPLAY_NAME_MAPPINGS = {'TM_LoadVideosFromFolder': 'Load Videos from Folder (Batch)'}
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']
