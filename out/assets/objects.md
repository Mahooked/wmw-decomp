# Objects format (Objects/*.hs)

Parsed 345 files; 12 distinct element paths.

'instances' counts how many times that element occurs across all
files; 'children' is the breakdown of what it contains.

element path                                         instances  attributes (value shape)
----------------------------------------------------------------------------------------------------
/InteractiveObject/Shapes/Shape/Point                     2096  pos:string/two floats
/InteractiveObject/DefaultProperties/Property             1384  name:string  value:asset path/float/four floats/int/string/three floats/two floats
/InteractiveObject/Sprites/Sprite                          798  angle:int  filename:asset path  gridSize:two floats  isBackground:bool  pos:string/two floats  sizeRefAnim:string  visible:bool
/InteractiveObject                                         345  
                                                                children: Sprites x345, DefaultProperties x322, Shapes x320, UVs x2, VertIndices x2
/InteractiveObject/Sprites                                 345  
                                                                children: Sprite x798
/InteractiveObject/Shapes/Shape                            329  
                                                                children: Point x2096
/InteractiveObject/DefaultProperties                       322  
                                                                children: Property x1384
/InteractiveObject/Shapes                                  320  
                                                                children: Shape x329
/InteractiveObject/VertIndices/Vert                         66  index:int
/InteractiveObject/UVs/UV                                   23  pos:two floats
/InteractiveObject/UVs                                       2  
                                                                children: UV x23
/InteractiveObject/VertIndices                               2  
                                                                children: Vert x66
